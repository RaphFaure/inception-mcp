"""
Serveur MCP pour INCEpTION.

Expose les opérations INCEpTION comme outils MCP utilisables par Claude.

Configuration (variables d'environnement) :
    INCEPTION_URL       URL de base (défaut : http://localhost:8080)
    INCEPTION_USER      Nom d'utilisateur
    INCEPTION_PASSWORD  Mot de passe

Lancement :
    python -m inception_mcp.server
    # ou via uv :
    uv run inception-mcp
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .client import InceptionClient, InceptionError, EXPORT_FORMATS

mcp = FastMCP(
    name="inception-mcp",
    instructions=(
        "Outils pour interagir avec un serveur INCEpTION (annotation NLP). "
        "Permet de gérer les projets, uploader des documents, importer/exporter "
        "des annotations et des projets complets, et suivre l'avancement."
    ),
)


def _client() -> InceptionClient:
    return InceptionClient(
        base_url=os.environ.get("INCEPTION_URL", "http://localhost:8080"),
        username=os.environ.get("INCEPTION_USER", "admin"),
        password=os.environ.get("INCEPTION_PASSWORD", ""),
    )


# ------------------------------------------------------------------
# Projects
# ------------------------------------------------------------------

@mcp.tool()
def list_projects() -> str:
    """Liste tous les projets INCEpTION accessibles."""
    projects = _client().list_projects()
    if not projects:
        return "Aucun projet."
    lines = [f"- [{p['id']}] {p['name']}" for p in projects]
    return "\n".join(lines)


@mcp.tool()
def create_project(name: str, description: str = "") -> str:
    """Crée un nouveau projet INCEpTION.

    Args:
        name: Nom du projet (sans espaces, utiliser underscores).
        description: Description optionnelle.
    """
    p = _client().create_project(name, description)
    return f"Projet créé : [{p['id']}] {p['name']}"


@mcp.tool()
def delete_project(project_id: int) -> str:
    """Supprime un projet INCEpTION et tous ses documents.

    ⚠️ Irréversible. Vérifier le project_id avant d'appeler.

    Args:
        project_id: ID numérique du projet.
    """
    _client().delete_project(project_id)
    return f"Projet [{project_id}] supprimé."


@mcp.tool()
def export_project_zip(project_id: int, output_path: str) -> str:
    """Exporte un projet complet (documents + annotations + schéma) en ZIP.

    Args:
        project_id: ID du projet.
        output_path: Chemin de sauvegarde du fichier ZIP.
    """
    content = _client().export_project_zip(project_id)
    Path(output_path).write_bytes(content)
    return f"Projet [{project_id}] exporté → {output_path} ({len(content) // 1024} Ko)"


@mcp.tool()
def import_project_zip(zip_path: str) -> str:
    """Importe un projet depuis un fichier ZIP exporté par INCEpTION.

    Args:
        zip_path: Chemin absolu vers le fichier ZIP.
    """
    p = _client().import_project_zip(Path(zip_path))
    return f"Projet importé : [{p['id']}] {p['name']}"


@mcp.tool()
def project_status(project_id: int) -> str:
    """Retourne l'état d'avancement d'un projet : documents et annotations par utilisateur.

    Args:
        project_id: ID du projet.
    """
    status = _client().project_status(project_id)
    lines = [f"Projet [{project_id}] — {status['n_documents']} document(s)\n"]
    for doc in status["documents"]:
        annotators = doc["annotators"]
        annot_str = ", ".join(
            f"{a['user']}:{a['state']}" for a in annotators
        ) if annotators else "aucune annotation"
        lines.append(f"  [{doc['doc_id']}] {doc['name']} (état: {doc['state']}) — {annot_str}")
    return "\n".join(lines)


# ------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------

@mcp.tool()
def list_documents(project_id: int) -> str:
    """Liste les documents d'un projet.

    Args:
        project_id: ID du projet.
    """
    docs = _client().list_documents(project_id)
    if not docs:
        return "Aucun document dans ce projet."
    lines = [f"- [{d['id']}] {d['name']} ({d['state']})" for d in docs]
    return "\n".join(lines)


@mcp.tool()
def upload_document(project_id: int, file_path: str, fmt: str = "text") -> str:
    """Upload un document dans un projet INCEpTION.

    Args:
        project_id: ID du projet cible.
        file_path: Chemin absolu vers le fichier à uploader.
        fmt: Format du document. Valeurs courantes : text, conllu, xmi, ctsv3.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")
    doc = _client().upload_document_from_file(project_id, path, fmt)
    return f"Document uploadé : [{doc['id']}] {doc['name']} (état : {doc['state']})"


@mcp.tool()
def batch_upload(project_id: int, folder_path: str, fmt: str = "text", glob: str = "*") -> str:
    """Uploade tous les fichiers d'un dossier dans un projet INCEpTION.

    Args:
        project_id: ID du projet cible.
        folder_path: Chemin absolu du dossier contenant les fichiers.
        fmt: Format des documents (text, conllu, xmi, ctsv3).
        glob: Pattern de sélection des fichiers (ex: "*.txt"). Défaut : tous.
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        raise NotADirectoryError(f"Dossier introuvable : {folder_path}")
    results = _client().batch_upload(project_id, folder, fmt, glob)
    if not results:
        return "Aucun fichier trouvé."
    lines = [f"- {r['file']} → [{r['doc']['id']}] ({r['doc']['state']})" for r in results]
    return f"{len(results)} fichier(s) uploadé(s) :\n" + "\n".join(lines)


@mcp.tool()
def export_document_source(
    project_id: int, document_id: int, output_path: str, fmt: str = "text"
) -> str:
    """Exporte le contenu source d'un document.

    Args:
        project_id: ID du projet.
        document_id: ID du document.
        output_path: Chemin de sauvegarde.
        fmt: Format d'export (text, conllu, xmi…).
    """
    content = _client().export_document_source(project_id, document_id, fmt)
    Path(output_path).write_bytes(content)
    return f"Document [{document_id}] exporté → {output_path} ({len(content)} octets)"


@mcp.tool()
def delete_document(project_id: int, document_id: int) -> str:
    """Supprime un document d'un projet.

    ⚠️ Irréversible.

    Args:
        project_id: ID du projet.
        document_id: ID du document.
    """
    _client().delete_document(project_id, document_id)
    return f"Document [{document_id}] supprimé du projet [{project_id}]."


# ------------------------------------------------------------------
# Annotations
# ------------------------------------------------------------------

@mcp.tool()
def list_annotations(project_id: int, document_id: int) -> str:
    """Liste les annotations existantes sur un document (par utilisateur).

    Args:
        project_id: ID du projet.
        document_id: ID du document.
    """
    annots = _client().list_annotations(project_id, document_id)
    if not annots:
        return "Aucune annotation sur ce document."
    lines = [f"- {a.get('user', '?')} : {a.get('state', '?')}" for a in annots]
    return "\n".join(lines)


@mcp.tool()
def export_annotations(
    project_id: int,
    document_id: int,
    user: str,
    fmt: str = "ctsv3",
    output_path: str = "",
) -> str:
    """Exporte les annotations d'un document vers un fichier.

    Args:
        project_id: ID du projet.
        document_id: ID du document.
        user: Nom de l'annotateur.
        fmt: Format d'export (ctsv3, xmi, conllu, text, jsoncas, nif, tcf).
        output_path: Chemin de sauvegarde (optionnel). Si vide, retourne le contenu texte.
    """
    content = _client().export_annotations(project_id, document_id, user, fmt)
    if output_path:
        Path(output_path).write_bytes(content)
        return f"Annotations exportées → {output_path} ({len(content)} octets)"
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return f"[Contenu binaire, {len(content)} octets — spécifier output_path pour sauvegarder]"


@mcp.tool()
def export_all_annotations(
    project_id: int,
    user: str,
    output_dir: str,
    fmt: str = "ctsv3",
) -> str:
    """Exporte les annotations de tous les documents d'un projet vers un dossier.

    Args:
        project_id: ID du projet.
        user: Nom de l'annotateur.
        output_dir: Dossier de destination (créé si absent).
        fmt: Format d'export (ctsv3, xmi, conllu…).
    """
    results = _client().export_all_annotations(project_id, user, Path(output_dir), fmt)
    ok = [r for r in results if r["ok"]]
    errors = [r for r in results if not r["ok"]]
    lines = [f"{len(ok)}/{len(results)} documents exportés → {output_dir}"]
    if errors:
        lines.append("Erreurs :")
        for r in errors:
            lines.append(f"  - {r['doc']} : {r['error']}")
    return "\n".join(lines)


@mcp.tool()
def import_annotations(
    project_id: int,
    document_id: int,
    user: str,
    file_path: str,
    fmt: str = "ctsv3",
    state: str = "IN_PROGRESS",
) -> str:
    """Importe des annotations depuis un fichier pour un utilisateur sur un document.

    Args:
        project_id: ID du projet.
        document_id: ID du document.
        user: Nom de l'annotateur cible.
        file_path: Chemin du fichier d'annotations.
        fmt: Format du fichier (ctsv3, xmi, conllu…).
        state: État d'annotation après import (IN_PROGRESS, COMPLETE).
    """
    content = Path(file_path).read_bytes()
    _client().import_annotations(project_id, document_id, user, content, fmt, state)
    return f"Annotations importées pour {user} sur document [{document_id}]."


@mcp.tool()
def delete_annotations(project_id: int, document_id: int, user: str) -> str:
    """Supprime toutes les annotations d'un utilisateur sur un document.

    ⚠️ Irréversible.

    Args:
        project_id: ID du projet.
        document_id: ID du document.
        user: Nom de l'annotateur.
    """
    _client().delete_annotations(project_id, document_id, user)
    return f"Annotations de {user} supprimées sur document [{document_id}]."


# ------------------------------------------------------------------
# Curation
# ------------------------------------------------------------------

@mcp.tool()
def export_curation(
    project_id: int,
    document_id: int,
    fmt: str = "ctsv3",
    output_path: str = "",
) -> str:
    """Exporte les annotations curées d'un document.

    Args:
        project_id: ID du projet.
        document_id: ID du document.
        fmt: Format d'export.
        output_path: Chemin de sauvegarde (optionnel).
    """
    content = _client().export_curation(project_id, document_id, fmt)
    if output_path:
        Path(output_path).write_bytes(content)
        return f"Curation exportée → {output_path} ({len(content)} octets)"
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return f"[Contenu binaire, {len(content)} octets]"


@mcp.tool()
def delete_curation(project_id: int, document_id: int) -> str:
    """Supprime les annotations curées d'un document.

    ⚠️ Irréversible.

    Args:
        project_id: ID du projet.
        document_id: ID du document.
    """
    _client().delete_curation(project_id, document_id)
    return f"Curation supprimée pour document [{document_id}]."


# ------------------------------------------------------------------
# Point d'entrée
# ------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
