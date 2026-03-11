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
        "Permet de gérer les projets, uploader des documents, lister et exporter des annotations."
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

    Args:
        project_id: ID numérique du projet.
    """
    _client().delete_project(project_id)
    return f"Projet [{project_id}] supprimé."


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
def delete_document(project_id: int, document_id: int) -> str:
    """Supprime un document d'un projet.

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
        user: Nom de l'annotateur dont on exporte les annotations.
        fmt: Format d'export. Options : ctsv3, xmi, conllu, text, jsoncas, nif, tcf.
        output_path: Chemin de sauvegarde (optionnel). Si vide, retourne le contenu texte.
    """
    content = _client().export_annotations(project_id, document_id, user, fmt)

    if output_path:
        Path(output_path).write_bytes(content)
        return f"Annotations exportées → {output_path} ({len(content)} octets)"

    # Retourner le texte si pas de fichier de sortie (pour formats textuels)
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return f"[Contenu binaire, {len(content)} octets — spécifier output_path pour sauvegarder]"


# ------------------------------------------------------------------
# Point d'entrée
# ------------------------------------------------------------------

def main():
    mcp.run()


if __name__ == "__main__":
    main()
