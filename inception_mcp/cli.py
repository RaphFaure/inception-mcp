"""
CLI INCEpTION — interface en ligne de commande pour les utilisateurs sans agent.

Usage :
    python -m inception_mcp.cli [OPTIONS] COMMAND

    Variables d'environnement (ou fichier .env) :
        INCEPTION_URL       http://localhost:8080
        INCEPTION_USER      admin
        INCEPTION_PASSWORD  ...

Exemples :
    python -m inception_mcp.cli list-projects
    python -m inception_mcp.cli list-documents --project 1
    python -m inception_mcp.cli upload --project 1 --file data.txt --format text
    python -m inception_mcp.cli export --project 1 --doc 0 --user admin --format ctsv3 --out annot.tsv
    python -m inception_mcp.cli delete-doc --project 1 --doc 0
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .client import InceptionClient, InceptionError, EXPORT_FORMATS


def get_client(args) -> InceptionClient:
    url = getattr(args, "url", None) or os.environ.get("INCEPTION_URL", "http://localhost:8080")
    user = getattr(args, "user", None) or os.environ.get("INCEPTION_USER", "admin")
    password = getattr(args, "password", None) or os.environ.get("INCEPTION_PASSWORD", "")
    return InceptionClient(url, user, password)


# ------------------------------------------------------------------
# Commandes
# ------------------------------------------------------------------

def cmd_list_projects(args):
    client = get_client(args)
    projects = client.list_projects()
    if not projects:
        print("Aucun projet.")
        return
    print(f"{'ID':<6} {'Nom'}")
    print("-" * 40)
    for p in projects:
        print(f"{p['id']:<6} {p['name']}")


def cmd_create_project(args):
    client = get_client(args)
    p = client.create_project(args.name, args.description or "")
    print(f"Projet créé : [{p['id']}] {p['name']}")


def cmd_delete_project(args):
    client = get_client(args)
    confirm = input(f"Supprimer le projet [{args.project}] ? (oui/non) : ")
    if confirm.strip().lower() not in ("oui", "o", "yes", "y"):
        print("Annulé.")
        return
    client.delete_project(args.project)
    print(f"Projet [{args.project}] supprimé.")


def cmd_list_documents(args):
    client = get_client(args)
    docs = client.list_documents(args.project)
    if not docs:
        print("Aucun document.")
        return
    print(f"{'ID':<6} {'État':<12} {'Nom'}")
    print("-" * 60)
    for d in docs:
        print(f"{d['id']:<6} {d['state']:<12} {d['name']}")


def cmd_upload(args):
    client = get_client(args)
    path = Path(args.file)
    if not path.exists():
        print(f"Fichier introuvable : {args.file}", file=sys.stderr)
        sys.exit(1)
    doc = client.upload_document_from_file(args.project, path, args.format)
    print(f"Uploadé : [{doc['id']}] {doc['name']} (état : {doc['state']})")


def cmd_delete_document(args):
    client = get_client(args)
    client.delete_document(args.project, args.doc)
    print(f"Document [{args.doc}] supprimé.")


def cmd_list_annotations(args):
    client = get_client(args)
    annots = client.list_annotations(args.project, args.doc)
    if not annots:
        print("Aucune annotation.")
        return
    for a in annots:
        print(f"- {a.get('user', '?')} : {a.get('state', '?')}")


def cmd_export(args):
    client = get_client(args)
    content = client.export_annotations(args.project, args.doc, args.user, args.format)
    if args.out:
        Path(args.out).write_bytes(content)
        print(f"Exporté → {args.out} ({len(content)} octets)")
    else:
        sys.stdout.buffer.write(content)


# ------------------------------------------------------------------
# Parser
# ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inception-cli",
        description="CLI pour INCEpTION via l'API REST AERO v1",
    )
    parser.add_argument("--url", default=None, help="URL INCEpTION (défaut : $INCEPTION_URL)")
    parser.add_argument("--user", default=None, help="Utilisateur (défaut : $INCEPTION_USER)")
    parser.add_argument("--password", default=None, help="Mot de passe (défaut : $INCEPTION_PASSWORD)")

    sub = parser.add_subparsers(dest="command", required=True)

    # list-projects
    sub.add_parser("list-projects", help="Lister les projets")

    # create-project
    cp = sub.add_parser("create-project", help="Créer un projet")
    cp.add_argument("--name", required=True)
    cp.add_argument("--description", default="")

    # delete-project
    dp = sub.add_parser("delete-project", help="Supprimer un projet")
    dp.add_argument("--project", type=int, required=True)

    # list-documents
    ld = sub.add_parser("list-documents", help="Lister les documents d'un projet")
    ld.add_argument("--project", type=int, required=True)

    # upload
    up = sub.add_parser("upload", help="Uploader un document")
    up.add_argument("--project", type=int, required=True)
    up.add_argument("--file", required=True)
    up.add_argument("--format", default="text", choices=["text", "conllu", "xmi", "ctsv3"])

    # delete-doc
    dd = sub.add_parser("delete-doc", help="Supprimer un document")
    dd.add_argument("--project", type=int, required=True)
    dd.add_argument("--doc", type=int, required=True)

    # list-annotations
    la = sub.add_parser("list-annotations", help="Lister les annotations d'un document")
    la.add_argument("--project", type=int, required=True)
    la.add_argument("--doc", type=int, required=True)

    # export
    ex = sub.add_parser("export", help="Exporter les annotations d'un document")
    ex.add_argument("--project", type=int, required=True)
    ex.add_argument("--doc", type=int, required=True)
    ex.add_argument("--user", required=True)
    ex.add_argument("--format", default="ctsv3", choices=EXPORT_FORMATS)
    ex.add_argument("--out", default=None, help="Fichier de sortie (défaut : stdout)")

    return parser


COMMANDS = {
    "list-projects": cmd_list_projects,
    "create-project": cmd_create_project,
    "delete-project": cmd_delete_project,
    "list-documents": cmd_list_documents,
    "upload": cmd_upload,
    "delete-doc": cmd_delete_document,
    "list-annotations": cmd_list_annotations,
    "export": cmd_export,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        COMMANDS[args.command](args)
    except InceptionError as e:
        print(f"Erreur INCEpTION : {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
