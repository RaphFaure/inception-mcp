# inception-mcp

MCP server and CLI for [INCEpTION](https://inception-project.github.io/), the open-source web annotation platform.

When used with an MCP-compatible agent such as Claude Code, INCEpTION operations
can be triggered directly from a conversation:

```
"Upload all .txt files in gutenberg/processed/ to project 1."
"Export annotations for document 42 by user admin in ctsv3 format to data/annot.tsv."
```

Exposes INCEpTION's AERO v1 REST API as:
- **MCP tools** — callable directly from Claude Code or Claude Desktop
- **CLI** — standalone terminal interface, no AI agent required

Both share the same underlying `InceptionClient`, ensuring consistent behaviour.

### Use cases

| Scenario | How |
|----------|-----|
| Corpus upload at scale | Ask Claude to batch-upload hundreds of documents to a project |
| Annotation pipeline automation | Chain upload → annotate → export in a single Claude conversation |
| Progress monitoring | Ask Claude to list all documents and their annotation states |
| Export and post-processing | Export ctsv3/XMI annotations and pipe them into a parsing script |
| Multi-project management | Create, inspect and archive projects without leaving the terminal |

---

## Features

| Feature | MCP server | CLI |
|---------|-----------|-----|
| List / create / delete projects | ✓ | ✓ |
| Export / import project ZIP (schema + docs + annotations) | ✓ | ✓ |
| Project progress status | ✓ | ✓ |
| List / upload / delete documents | ✓ | ✓ |
| Batch upload a folder of documents | ✓ | ✓ |
| Export document source | ✓ | ✓ |
| List annotations by user | ✓ | ✓ |
| Export / import annotations (13 formats) | ✓ | ✓ |
| Export all annotations for a project | ✓ | ✓ |
| Delete annotations by user | ✓ | ✓ |
| Export / delete curation layer | ✓ | ✓ |

Supported export formats: `ctsv3`, `xmi`, `xmi-struct`, `conllu`, `conll2003`, `conll2006`, `conll2009`, `conll2012`, `text`, `tcf`, `jsoncas`, `jsoncas-struct`, `nif`.

---

## Requirements

- Python ≥ 3.10
- A running INCEpTION instance (tested with INCEpTION 33+) **with the REST API enabled** (see below)
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`

---

## Enabling the INCEpTION REST API

The AERO v1 REST API is **disabled by default** in INCEpTION. You must enable it once before using this package.

1. Log in to INCEpTION as an administrator.
2. Go to **Administration → Settings** (top-right menu).
3. Under the **API** tab, check **Enable REST API**.
4. Click **Save**.

The API is now reachable at `http://<host>:<port>/api/aero/v1`. You can verify it by opening the Swagger UI:

```
http://localhost:8080/swagger-ui.html
```

> **Note on authentication**: the REST API uses HTTP Basic Auth. Use the same username and password as your INCEpTION login. Creating a dedicated user with limited permissions (e.g. Project Manager role only) is recommended for production use.

---

## Installation

### With uv (recommended)

```bash
git clone https://github.com/RaphFaure/inception-mcp
cd inception-mcp
uv sync
```

### With pip

```bash
git clone https://github.com/RaphFaure/inception-mcp
cd inception-mcp
pip install -e .
```

---

## Configuration

Connection parameters are read from environment variables (or a `.env` file at the project root):

| Variable | Default | Description |
|----------|---------|-------------|
| `INCEPTION_URL` | `http://localhost:8080` | Base URL of the INCEpTION instance |
| `INCEPTION_USER` | `admin` | Username |
| `INCEPTION_PASSWORD` | *(empty)* | Password |

Create a `.env` file:

```bash
cp .env.example .env
# then edit .env with your credentials
```

---

## Usage — MCP server

### Claude Desktop

Add the following block to your `~/.claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "inception": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/inception-mcp", "inception-mcp"],
      "env": {
        "INCEPTION_URL": "http://localhost:8080",
        "INCEPTION_USER": "admin",
        "INCEPTION_PASSWORD": "your_password"
      }
    }
  }
}
```

Restart Claude Desktop. The INCEpTION tools will appear automatically.

### Claude Code (claude.ai/code)

Add the same block under `mcpServers` in your project's `.claude/settings.json` or in `~/.claude/settings.json`.

### Available MCP tools

**Projects**

| Tool | Description |
|------|-------------|
| `list_projects` | List all accessible projects |
| `create_project(name, description?)` | Create a new project |
| `delete_project(project_id)` | ⚠️ Delete a project and all its documents |
| `export_project_zip(project_id, output_path)` | Export full project as ZIP |
| `import_project_zip(zip_path)` | Import a project from ZIP |
| `project_status(project_id)` | Show annotation progress per document |

**Documents**

| Tool | Description |
|------|-------------|
| `list_documents(project_id)` | List documents in a project |
| `upload_document(project_id, file_path, fmt?)` | Upload a single file |
| `batch_upload(project_id, folder_path, fmt?, glob?)` | Upload all files in a folder |
| `export_document_source(project_id, document_id, output_path, fmt?)` | Export document source |
| `delete_document(project_id, document_id)` | ⚠️ Delete a document |

**Annotations**

| Tool | Description |
|------|-------------|
| `list_annotations(project_id, document_id)` | List annotations per user |
| `export_annotations(project_id, document_id, user, fmt?, output_path?)` | Export annotations |
| `export_all_annotations(project_id, user, output_dir, fmt?)` | Export all docs in a project |
| `import_annotations(project_id, document_id, user, file_path, fmt?, state?)` | Import annotations |
| `delete_annotations(project_id, document_id, user)` | ⚠️ Delete a user's annotations |

**Curation**

| Tool | Description |
|------|-------------|
| `export_curation(project_id, document_id, fmt?, output_path?)` | Export curated annotations |
| `delete_curation(project_id, document_id)` | ⚠️ Delete curated annotations |

---

## Usage — CLI

```bash
# via uv
uv run inception-cli <command>

# or, if installed via pip
inception-cli <command>
```

### Global options

```
--url       URL INCEpTION  (overrides $INCEPTION_URL)
--user      Username        (overrides $INCEPTION_USER)
--password  Password        (overrides $INCEPTION_PASSWORD)
```

### Commands

```bash
# Projects
inception-cli list-projects
inception-cli create-project --name my_project
inception-cli status --project 1
inception-cli export-project --project 1 --out backup.zip
inception-cli import-project --zip backup.zip
inception-cli delete-project --project 1

# Documents
inception-cli list-documents --project 1
inception-cli upload --project 1 --file doc.txt --format text
inception-cli batch-upload --project 1 --folder ./texts --glob "*.txt"
inception-cli export-doc-source --project 1 --doc 42 --out source.txt
inception-cli delete-doc --project 1 --doc 42

# Annotations
inception-cli list-annotations --project 1 --doc 42
inception-cli export --project 1 --doc 42 --user admin --format ctsv3 --out annot.tsv
inception-cli export-all --project 1 --user admin --out-dir ./annotations
inception-cli import-annotations --project 1 --doc 42 --user admin --file annot.tsv
inception-cli delete-annotations --project 1 --doc 42 --user admin

# Curation
inception-cli export-curation --project 1 --doc 42 --format ctsv3 --out curation.tsv
inception-cli delete-curation --project 1 --doc 42
```

---

## Architecture

```
inception_mcp/
├── __init__.py      # Public exports: InceptionClient, InceptionError
├── client.py        # InceptionClient — HTTP layer over AERO v1 REST API
├── server.py        # FastMCP server — wraps client as MCP tools
└── cli.py           # argparse CLI — wraps client as shell commands
tests/
└── test_client.py   # Unit tests (22 tests, no INCEpTION instance required)
```

`client.py` is the single source of truth for all API calls. Adding a new operation means implementing it once in `InceptionClient`, then exposing it in `server.py` (as a `@mcp.tool()`) and in `cli.py` (as a new subcommand).

Run tests with:

```bash
pip install pytest
pytest tests/
```

---

## Security notes

> **Destructive operations are irreversible.**
> `delete_project`, `delete_document`, `delete_annotations` and `delete_curation`
> have no undo mechanism in INCEpTION. Always verify IDs before calling them.

The server runs locally and is only reachable from the machine where it is started.
Credentials are read from environment variables — never hard-code them in files
committed to version control. The `.gitignore` in this repository excludes `.env`.

---

## INCEpTION API reference

The full AERO v1 Swagger UI is available at:

```
http://<your-inception-host>:<port>/swagger-ui.html
```

---

## License

[MIT](LICENSE) — you are free to use, modify, and redistribute this software in any project, commercial or not, as long as the original copyright notice is kept.
