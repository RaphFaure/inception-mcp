"""
Couche d'accès à l'API REST AERO v1 d'INCEpTION.

Toutes les opérations réseau passent par cette classe.
Utilisée aussi bien par le serveur MCP que par la CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests

EXPORT_FORMATS = [
    "ctsv3", "xmi", "xmi-struct", "conllu", "conll2003",
    "conll2006", "conll2009", "conll2012", "text", "tcf",
    "jsoncas", "jsoncas-struct", "nif",
]


class InceptionError(Exception):
    pass


class InceptionClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: int = 30):
        self.base = base_url.rstrip("/") + "/api/aero/v1"
        self.auth = (username, password)
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get(self, path: str, **kwargs) -> Any:
        resp = requests.get(f"{self.base}{path}", auth=self.auth, timeout=self.timeout, **kwargs)
        return self._parse(resp)

    def _post(self, path: str, **kwargs) -> Any:
        resp = requests.post(f"{self.base}{path}", auth=self.auth, timeout=self.timeout, **kwargs)
        return self._parse(resp)

    def _delete(self, path: str) -> Any:
        resp = requests.delete(f"{self.base}{path}", auth=self.auth, timeout=self.timeout)
        return self._parse(resp)

    def _parse(self, resp: requests.Response) -> Any:
        try:
            data = resp.json()
        except Exception:
            raise InceptionError(f"Réponse non-JSON ({resp.status_code}): {resp.text[:200]}")

        errors = [m["message"] for m in data.get("messages", []) if m.get("level") == "ERROR"]
        if errors:
            raise InceptionError("; ".join(errors))

        return data.get("body")

    def _get_binary(self, path: str, **kwargs) -> bytes:
        """GET qui retourne du contenu binaire (ZIP, fichiers annotés)."""
        resp = requests.get(f"{self.base}{path}", auth=self.auth, timeout=self.timeout, **kwargs)
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            data = resp.json()
            errors = [m["message"] for m in data.get("messages", []) if m.get("level") == "ERROR"]
            if errors:
                raise InceptionError("; ".join(errors))
        if resp.status_code != 200:
            raise InceptionError(f"Requête échouée ({resp.status_code})")
        return resp.content

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def list_projects(self) -> list[dict]:
        return self._get("/projects") or []

    def create_project(self, name: str, description: str = "") -> dict:
        return self._post("/projects", data={"name": name, "description": description})

    def delete_project(self, project_id: int) -> None:
        self._delete(f"/projects/{project_id}")

    def export_project_zip(self, project_id: int) -> bytes:
        """Exporte le projet complet (documents + annotations + schéma) en ZIP."""
        return self._get_binary(f"/projects/{project_id}/export.zip")

    def import_project_zip(self, zip_path: Path) -> dict:
        """Importe un projet depuis un fichier ZIP exporté par INCEpTION."""
        content = zip_path.read_bytes()
        resp = requests.post(
            f"{self.base}/projects/import",
            auth=self.auth,
            timeout=max(self.timeout, 120),
            files={"file": (zip_path.name, content, "application/zip")},
        )
        return self._parse(resp)

    # ------------------------------------------------------------------
    # Documents
    # ------------------------------------------------------------------
    def list_documents(self, project_id: int) -> list[dict]:
        return self._get(f"/projects/{project_id}/documents") or []

    def upload_document(
        self,
        project_id: int,
        name: str,
        content: str | bytes,
        fmt: str = "text",
    ) -> dict:
        if isinstance(content, str):
            content = content.encode("utf-8")
        return self._post(
            f"/projects/{project_id}/documents",
            data={"name": name, "format": fmt},
            files={"content": (name, content)},
        )

    def upload_document_from_file(
        self,
        project_id: int,
        path: Path,
        fmt: str = "text",
    ) -> dict:
        content = path.read_bytes()
        return self.upload_document(project_id, path.name, content, fmt)

    def batch_upload(
        self,
        project_id: int,
        folder: Path,
        fmt: str = "text",
        glob: str = "*",
    ) -> list[dict]:
        """Uploade tous les fichiers d'un dossier correspondant au pattern glob."""
        results = []
        for path in sorted(folder.glob(glob)):
            if path.is_file():
                doc = self.upload_document_from_file(project_id, path, fmt)
                results.append({"file": path.name, "doc": doc})
        return results

    def export_document_source(
        self,
        project_id: int,
        document_id: int,
        fmt: str = "text",
    ) -> bytes:
        """Exporte le contenu source d'un document (texte brut ou format d'origine)."""
        return self._get_binary(
            f"/projects/{project_id}/documents/{document_id}",
            params={"format": fmt},
        )

    def delete_document(self, project_id: int, document_id: int) -> None:
        self._delete(f"/projects/{project_id}/documents/{document_id}")

    # ------------------------------------------------------------------
    # Annotations
    # ------------------------------------------------------------------
    def list_annotations(self, project_id: int, document_id: int) -> list[dict]:
        return self._get(f"/projects/{project_id}/documents/{document_id}/annotations") or []

    def export_annotations(
        self,
        project_id: int,
        document_id: int,
        user: str,
        fmt: str = "ctsv3",
    ) -> bytes:
        return self._get_binary(
            f"/projects/{project_id}/documents/{document_id}/annotations/{user}",
            params={"format": fmt},
        )

    def import_annotations(
        self,
        project_id: int,
        document_id: int,
        user: str,
        content: bytes,
        fmt: str = "ctsv3",
        state: str = "IN_PROGRESS",
    ) -> dict:
        """Importe des annotations pour un utilisateur sur un document."""
        resp = requests.post(
            f"{self.base}/projects/{project_id}/documents/{document_id}/annotations/{user}",
            auth=self.auth,
            timeout=self.timeout,
            data={"format": fmt, "state": state},
            files={"content": ("annotations", content)},
        )
        return self._parse(resp)

    def delete_annotations(self, project_id: int, document_id: int, user: str) -> None:
        """Supprime toutes les annotations d'un utilisateur sur un document."""
        self._delete(
            f"/projects/{project_id}/documents/{document_id}/annotations/{user}"
        )

    def export_all_annotations(
        self,
        project_id: int,
        user: str,
        output_dir: Path,
        fmt: str = "ctsv3",
    ) -> list[dict]:
        """Exporte les annotations de tous les documents d'un projet vers un dossier."""
        output_dir.mkdir(parents=True, exist_ok=True)
        docs = self.list_documents(project_id)
        results = []
        for doc in docs:
            doc_id = doc["id"]
            doc_name = doc["name"]
            try:
                content = self.export_annotations(project_id, doc_id, user, fmt)
                ext = fmt.split("-")[0]
                out_path = output_dir / f"{Path(doc_name).stem}.{ext}"
                out_path.write_bytes(content)
                results.append({"doc": doc_name, "path": str(out_path), "ok": True})
            except InceptionError as e:
                results.append({"doc": doc_name, "error": str(e), "ok": False})
        return results

    def project_status(self, project_id: int) -> dict:
        """Retourne un résumé de l'avancement d'un projet (documents + états d'annotation)."""
        docs = self.list_documents(project_id)
        summary = []
        for doc in docs:
            doc_id = doc["id"]
            annots = self.list_annotations(project_id, doc_id)
            summary.append({
                "doc_id": doc_id,
                "name": doc["name"],
                "state": doc.get("state"),
                "annotators": [
                    {"user": a.get("user"), "state": a.get("state")}
                    for a in annots
                ],
            })
        return {"project_id": project_id, "n_documents": len(docs), "documents": summary}

    # ------------------------------------------------------------------
    # Curation
    # ------------------------------------------------------------------
    def export_curation(
        self,
        project_id: int,
        document_id: int,
        fmt: str = "ctsv3",
    ) -> bytes:
        """Exporte les annotations curées d'un document."""
        return self._get_binary(
            f"/projects/{project_id}/documents/{document_id}/curation",
            params={"format": fmt},
        )

    def delete_curation(self, project_id: int, document_id: int) -> None:
        """Supprime les annotations curées d'un document."""
        self._delete(f"/projects/{project_id}/documents/{document_id}/curation")
