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

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------
    def list_projects(self) -> list[dict]:
        return self._get("/projects") or []

    def create_project(self, name: str, description: str = "") -> dict:
        return self._post("/projects", data={"name": name, "description": description})

    def delete_project(self, project_id: int) -> None:
        self._delete(f"/projects/{project_id}")

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
        resp = requests.get(
            f"{self.base}/projects/{project_id}/documents/{document_id}/annotations/{user}",
            auth=self.auth,
            timeout=self.timeout,
            params={"format": fmt},
        )
        # L'export peut retourner du binaire ou du JSON d'erreur
        ct = resp.headers.get("Content-Type", "")
        if "application/json" in ct:
            data = resp.json()
            errors = [m["message"] for m in data.get("messages", []) if m.get("level") == "ERROR"]
            if errors:
                raise InceptionError("; ".join(errors))
        if resp.status_code != 200:
            raise InceptionError(f"Export échoué ({resp.status_code})")
        return resp.content
