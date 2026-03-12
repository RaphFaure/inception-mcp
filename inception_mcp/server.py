"""
MCP server for INCEpTION.

Exposes INCEpTION operations as MCP tools usable by Claude.

Configuration (environment variables):
    INCEPTION_URL       Base URL (default: http://localhost:8080)
    INCEPTION_USER      Username
    INCEPTION_PASSWORD  Password

Launch:
    python -m inception_mcp.server
    # or via uv:
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
        "Tools to interact with an INCEpTION NLP annotation server. "
        "Manage projects, upload documents, import/export annotations and full projects, "
        "and track annotation progress."
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
    """List all accessible INCEpTION projects."""
    projects = _client().list_projects()
    if not projects:
        return "Aucun projet."
    lines = [f"- [{p['id']}] {p['name']}" for p in projects]
    return "\n".join(lines)


@mcp.tool()
def create_project(name: str, description: str = "") -> str:
    """Create a new INCEpTION project.

    Args:
        name: Project name (no spaces; use underscores).
        description: Optional description.
    """
    p = _client().create_project(name, description)
    return f"Projet créé : [{p['id']}] {p['name']}"


@mcp.tool()
def delete_project(project_id: int) -> str:
    """Delete an INCEpTION project and all its documents.

    WARNING: Irreversible. Verify the project_id before calling.

    Args:
        project_id: Numeric project ID.
    """
    _client().delete_project(project_id)
    return f"Projet [{project_id}] supprimé."


@mcp.tool()
def export_project_zip(project_id: int, output_path: str) -> str:
    """Export a complete project (documents + annotations + schema) as a ZIP file.

    Args:
        project_id: Project ID.
        output_path: Path where the ZIP file will be saved.
    """
    content = _client().export_project_zip(project_id)
    Path(output_path).write_bytes(content)
    return f"Projet [{project_id}] exporté → {output_path} ({len(content) // 1024} Ko)"


@mcp.tool()
def import_project_zip(zip_path: str) -> str:
    """Import a project from a ZIP file exported by INCEpTION.

    Args:
        zip_path: Absolute path to the ZIP file.
    """
    p = _client().import_project_zip(Path(zip_path))
    return f"Projet importé : [{p['id']}] {p['name']}"


@mcp.tool()
def project_status(project_id: int) -> str:
    """Return the annotation progress of a project: documents and per-user annotation states.

    Args:
        project_id: Project ID.
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
    """List the documents in a project.

    Args:
        project_id: Project ID.
    """
    docs = _client().list_documents(project_id)
    if not docs:
        return "Aucun document dans ce projet."
    lines = [f"- [{d['id']}] {d['name']} ({d['state']})" for d in docs]
    return "\n".join(lines)


@mcp.tool()
def upload_document(project_id: int, file_path: str, fmt: str = "text") -> str:
    """Upload a document to an INCEpTION project.

    Args:
        project_id: Target project ID.
        file_path: Absolute path to the file to upload.
        fmt: Document format. Common values: text, conllu, xmi, ctsv3.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")
    doc = _client().upload_document_from_file(project_id, path, fmt)
    return f"Document uploadé : [{doc['id']}] {doc['name']} (état : {doc['state']})"


@mcp.tool()
def batch_upload(project_id: int, folder_path: str, fmt: str = "text", glob: str = "*") -> str:
    """Upload all files from a folder into an INCEpTION project.

    Args:
        project_id: Target project ID.
        folder_path: Absolute path to the folder containing the files.
        fmt: Document format (text, conllu, xmi, ctsv3).
        glob: File selection pattern (e.g. "*.txt"). Default: all files.
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
    """Export the source content of a document.

    Args:
        project_id: Project ID.
        document_id: Document ID.
        output_path: Path where the file will be saved.
        fmt: Export format (text, conllu, xmi, …).
    """
    if fmt not in EXPORT_FORMATS:
        return f"Invalid format '{fmt}'. Accepted values: {', '.join(EXPORT_FORMATS)}"
    content = _client().export_document_source(project_id, document_id, fmt)
    Path(output_path).write_bytes(content)
    return f"Document [{document_id}] exporté → {output_path} ({len(content)} octets)"


@mcp.tool()
def delete_document(project_id: int, document_id: int) -> str:
    """Delete a document from a project.

    WARNING: Irreversible.

    Args:
        project_id: Project ID.
        document_id: Document ID.
    """
    _client().delete_document(project_id, document_id)
    return f"Document [{document_id}] supprimé du projet [{project_id}]."


# ------------------------------------------------------------------
# Annotations
# ------------------------------------------------------------------

@mcp.tool()
def list_annotations(project_id: int, document_id: int) -> str:
    """List existing annotations on a document, grouped by user.

    Args:
        project_id: Project ID.
        document_id: Document ID.
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
    """Export the annotations of a document to a file.

    Args:
        project_id: Project ID.
        document_id: Document ID.
        user: Annotator username.
        fmt: Export format (ctsv3, xmi, conllu, text, jsoncas, nif, tcf).
        output_path: Save path (optional). If empty, returns the content as text.
    """
    if fmt not in EXPORT_FORMATS:
        return f"Invalid format '{fmt}'. Accepted values: {', '.join(EXPORT_FORMATS)}"
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
    """Export annotations for all documents in a project to a folder.

    Args:
        project_id: Project ID.
        user: Annotator username.
        output_dir: Destination folder (created if it does not exist).
        fmt: Export format (ctsv3, xmi, conllu, …).
    """
    if fmt not in EXPORT_FORMATS:
        return f"Invalid format '{fmt}'. Accepted values: {', '.join(EXPORT_FORMATS)}"
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
    """Import annotations from a file for a user on a document.

    Args:
        project_id: Project ID.
        document_id: Document ID.
        user: Target annotator username.
        file_path: Path to the annotations file.
        fmt: File format (ctsv3, xmi, conllu, …).
        state: Annotation state after import (IN_PROGRESS, COMPLETE).
    """
    content = Path(file_path).read_bytes()
    _client().import_annotations(project_id, document_id, user, content, fmt, state)
    return f"Annotations importées pour {user} sur document [{document_id}]."


@mcp.tool()
def delete_annotations(project_id: int, document_id: int, user: str) -> str:
    """Delete all annotations by a user on a document.

    WARNING: Irreversible.

    Args:
        project_id: Project ID.
        document_id: Document ID.
        user: Annotator username.
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
    """Export the curated annotations of a document.

    Args:
        project_id: Project ID.
        document_id: Document ID.
        fmt: Export format.
        output_path: Save path (optional).
    """
    if fmt not in EXPORT_FORMATS:
        return f"Invalid format '{fmt}'. Accepted values: {', '.join(EXPORT_FORMATS)}"
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
    """Delete the curated annotations of a document.

    WARNING: Irreversible.

    Args:
        project_id: Project ID.
        document_id: Document ID.
    """
    _client().delete_curation(project_id, document_id)
    return f"Curation supprimée pour document [{document_id}]."


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
