"""
CLI INCEpTION — interface en ligne de commande pour les utilisateurs sans agent.

Usage :
    python -m inception_mcp.cli [OPTIONS] COMMAND

    Variables d'environnement (ou fichier .env) :
        INCEPTION_URL       http://localhost:8080
        INCEPTION_USER      admin
        INCEPTION_PASSWORD  ...

Exemples :
    inception-cli list-projects
    inception-cli list-documents --project 1
    inception-cli upload --project 1 --file data.txt --format text
    inception-cli batch-upload --project 1 --folder ./texts --glob "*.txt"
    inception-cli status --project 1
    inception-cli export --project 1 --doc 0 --user admin --format ctsv3 --out annot.tsv
    inception-cli export-all --project 1 --user admin --out-dir ./annotations
    inception-cli export-project --project 1 --out project_backup.zip
    inception-cli import-project --zip project_backup.zip
    inception-cli import-annotations --project 1 --doc 0 --user admin --file annot.tsv
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
# Commandes — Projects
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


def cmd_export_project(args):
    client = get_client(args)
    content = client.export_project_zip(args.project)
    Path(args.out).write_bytes(content)
    print(f"Projet [{args.project}] exporté → {args.out} ({len(content) // 1024} Ko)")


def cmd_import_project(args):
    client = get_client(args)
    p = client.import_project_zip(Path(args.zip))
    print(f"Projet importé : [{p['id']}] {p['name']}")


def cmd_project_status(args):
    client = get_client(args)
    status = client.project_status(args.project)
    print(f"Projet [{args.project}] — {status['n_documents']} document(s)")
    print(f"{'ID':<6} {'État doc':<20} {'Annotateurs'}")
    print("-" * 70)
    for doc in status["documents"]:
        annots = ", ".join(
            f"{a['user']}:{a['state']}" for a in doc["annotators"]
        ) or "—"
        print(f"{doc['doc_id']:<6} {doc['state']:<20} {doc['name']}  [{annots}]")


# ------------------------------------------------------------------
# Commandes — Documents
# ------------------------------------------------------------------

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


def cmd_batch_upload(args):
    client = get_client(args)
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Dossier introuvable : {args.folder}", file=sys.stderr)
        sys.exit(1)
    results = client.batch_upload(args.project, folder, args.format, args.glob)
    if not results:
        print("Aucun fichier trouvé.")
        return
    for r in results:
        print(f"  {r['file']} → [{r['doc']['id']}] ({r['doc']['state']})")
    print(f"Total : {len(results)} fichier(s) uploadé(s).")


def cmd_export_document_source(args):
    client = get_client(args)
    content = client.export_document_source(args.project, args.doc, args.format)
    if args.out:
        Path(args.out).write_bytes(content)
        print(f"Document [{args.doc}] exporté → {args.out}")
    else:
        sys.stdout.buffer.write(content)


def cmd_delete_document(args):
    client = get_client(args)
    client.delete_document(args.project, args.doc)
    print(f"Document [{args.doc}] supprimé.")


# ------------------------------------------------------------------
# Commandes — Annotations
# ------------------------------------------------------------------

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


def cmd_export_all(args):
    client = get_client(args)
    results = client.export_all_annotations(
        args.project, args.user, Path(args.out_dir), args.format
    )
    ok = [r for r in results if r["ok"]]
    errors = [r for r in results if not r["ok"]]
    print(f"{len(ok)}/{len(results)} documents exportés → {args.out_dir}")
    for r in errors:
        print(f"  ERREUR {r['doc']} : {r['error']}", file=sys.stderr)


def cmd_import_annotations(args):
    client = get_client(args)
    content = Path(args.file).read_bytes()
    client.import_annotations(
        args.project, args.doc, args.user, content, args.format, args.state
    )
    print(f"Annotations importées pour {args.user} sur document [{args.doc}].")


def cmd_delete_annotations(args):
    client = get_client(args)
    client.delete_annotations(args.project, args.doc, args.user)
    print(f"Annotations de {args.user} supprimées sur document [{args.doc}].")


# ------------------------------------------------------------------
# Commandes — Curation
# ------------------------------------------------------------------

def cmd_export_curation(args):
    client = get_client(args)
    content = client.export_curation(args.project, args.doc, args.format)
    if args.out:
        Path(args.out).write_bytes(content)
        print(f"Curation exportée → {args.out} ({len(content)} octets)")
    else:
        sys.stdout.buffer.write(content)


def cmd_delete_curation(args):
    client = get_client(args)
    client.delete_curation(args.project, args.doc)
    print(f"Curation supprimée pour document [{args.doc}].")


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

    # --- Projects ---
    sub.add_parser("list-projects", help="Lister les projets")

    cp = sub.add_parser("create-project", help="Créer un projet")
    cp.add_argument("--name", required=True)
    cp.add_argument("--description", default="")

    dp = sub.add_parser("delete-project", help="Supprimer un projet (irréversible)")
    dp.add_argument("--project", type=int, required=True)

    ep = sub.add_parser("export-project", help="Exporter un projet complet en ZIP")
    ep.add_argument("--project", type=int, required=True)
    ep.add_argument("--out", required=True, help="Fichier ZIP de sortie")

    ip = sub.add_parser("import-project", help="Importer un projet depuis un ZIP")
    ip.add_argument("--zip", required=True, help="Chemin du fichier ZIP")

    sp = sub.add_parser("status", help="Afficher l'avancement d'un projet")
    sp.add_argument("--project", type=int, required=True)

    # --- Documents ---
    ld = sub.add_parser("list-documents", help="Lister les documents d'un projet")
    ld.add_argument("--project", type=int, required=True)

    up = sub.add_parser("upload", help="Uploader un document")
    up.add_argument("--project", type=int, required=True)
    up.add_argument("--file", required=True)
    up.add_argument("--format", default="text", choices=["text", "conllu", "xmi", "ctsv3"])

    bu = sub.add_parser("batch-upload", help="Uploader tous les fichiers d'un dossier")
    bu.add_argument("--project", type=int, required=True)
    bu.add_argument("--folder", required=True)
    bu.add_argument("--format", default="text", choices=["text", "conllu", "xmi", "ctsv3"])
    bu.add_argument("--glob", default="*", help="Pattern de fichiers (ex: *.txt)")

    eds = sub.add_parser("export-doc-source", help="Exporter le source d'un document")
    eds.add_argument("--project", type=int, required=True)
    eds.add_argument("--doc", type=int, required=True)
    eds.add_argument("--format", default="text", choices=EXPORT_FORMATS)
    eds.add_argument("--out", default=None)

    dd = sub.add_parser("delete-doc", help="Supprimer un document (irréversible)")
    dd.add_argument("--project", type=int, required=True)
    dd.add_argument("--doc", type=int, required=True)

    # --- Annotations ---
    la = sub.add_parser("list-annotations", help="Lister les annotations d'un document")
    la.add_argument("--project", type=int, required=True)
    la.add_argument("--doc", type=int, required=True)

    ex = sub.add_parser("export", help="Exporter les annotations d'un document")
    ex.add_argument("--project", type=int, required=True)
    ex.add_argument("--doc", type=int, required=True)
    ex.add_argument("--user", required=True)
    ex.add_argument("--format", default="ctsv3", choices=EXPORT_FORMATS)
    ex.add_argument("--out", default=None)

    ea = sub.add_parser("export-all", help="Exporter toutes les annotations d'un projet")
    ea.add_argument("--project", type=int, required=True)
    ea.add_argument("--user", required=True)
    ea.add_argument("--out-dir", required=True)
    ea.add_argument("--format", default="ctsv3", choices=EXPORT_FORMATS)

    ia = sub.add_parser("import-annotations", help="Importer des annotations")
    ia.add_argument("--project", type=int, required=True)
    ia.add_argument("--doc", type=int, required=True)
    ia.add_argument("--user", required=True)
    ia.add_argument("--file", required=True)
    ia.add_argument("--format", default="ctsv3", choices=EXPORT_FORMATS)
    ia.add_argument("--state", default="IN_PROGRESS", choices=["IN_PROGRESS", "COMPLETE"])

    da = sub.add_parser("delete-annotations", help="Supprimer les annotations d'un utilisateur")
    da.add_argument("--project", type=int, required=True)
    da.add_argument("--doc", type=int, required=True)
    da.add_argument("--user", required=True)

    # --- Curation ---
    ec = sub.add_parser("export-curation", help="Exporter la curation d'un document")
    ec.add_argument("--project", type=int, required=True)
    ec.add_argument("--doc", type=int, required=True)
    ec.add_argument("--format", default="ctsv3", choices=EXPORT_FORMATS)
    ec.add_argument("--out", default=None)

    dc = sub.add_parser("delete-curation", help="Supprimer la curation d'un document")
    dc.add_argument("--project", type=int, required=True)
    dc.add_argument("--doc", type=int, required=True)

    return parser


COMMANDS = {
    "list-projects":      cmd_list_projects,
    "create-project":     cmd_create_project,
    "delete-project":     cmd_delete_project,
    "export-project":     cmd_export_project,
    "import-project":     cmd_import_project,
    "status":             cmd_project_status,
    "list-documents":     cmd_list_documents,
    "upload":             cmd_upload,
    "batch-upload":       cmd_batch_upload,
    "export-doc-source":  cmd_export_document_source,
    "delete-doc":         cmd_delete_document,
    "list-annotations":   cmd_list_annotations,
    "export":             cmd_export,
    "export-all":         cmd_export_all,
    "import-annotations": cmd_import_annotations,
    "delete-annotations": cmd_delete_annotations,
    "export-curation":    cmd_export_curation,
    "delete-curation":    cmd_delete_curation,
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
