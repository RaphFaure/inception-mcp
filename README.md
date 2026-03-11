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
| List / upload / delete documents | ✓ | ✓ |
| List annotations by user | ✓ | ✓ |
| Export annotations (13 formats) | ✓ | ✓ |

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
git clone https://github.com/your-org/inception-mcp
cd inception-mcp
uv sync
```

### With pip

```bash
git clone https://github.com/your-org/inception-mcp
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

Restart Claude Desktop. The 8 INCEpTION tools will appear automatically.

### Claude Code (claude.ai/code)

Add the same block under `mcpServers` in your project's `.claude/settings.json` or in `~/.claude/settings.json`.

### Available MCP tools

| Tool | Description |
|------|-------------|
| `list_projects` | List all accessible projects |
| `create_project(name, description?)` | Create a new project |
| `delete_project(project_id)` | Delete a project and all its documents |
| `list_documents(project_id)` | List documents in a project |
| `upload_document(project_id, file_path, fmt?)` | Upload a file (default format: `text`) |
| `delete_document(project_id, document_id)` | Delete a document |
| `list_annotations(project_id, document_id)` | List annotations per user |
| `export_annotations(project_id, document_id, user, fmt?, output_path?)` | Export annotations |

---

## Usage — CLI

The CLI exposes the same operations without requiring an AI agent.

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
inception-cli create-project --name my_project --description "Optional description"
inception-cli delete-project --project 1

# Documents
inception-cli list-documents --project 1
inception-cli upload --project 1 --file path/to/doc.txt --format text
inception-cli delete-doc --project 1 --doc 42

# Annotations
inception-cli list-annotations --project 1 --doc 42
inception-cli export --project 1 --doc 42 --user admin --format ctsv3 --out annot.tsv
inception-cli export --project 1 --doc 42 --user admin --format xmi   # stdout
```

---

## Architecture

```
inception_mcp/
├── __init__.py      # Public exports: InceptionClient, InceptionError
├── client.py        # InceptionClient — HTTP layer over AERO v1 REST API
├── server.py        # FastMCP server — wraps client as MCP tools
└── cli.py           # argparse CLI — wraps client as shell commands
```

`client.py` is the single source of truth for all API calls. Adding a new operation means implementing it once in `InceptionClient`, then exposing it in `server.py` (as a `@mcp.tool()`) and in `cli.py` (as a new subcommand).

---

## Security notes

> **Destructive operations are irreversible.**
> `delete_project` permanently removes a project and all its documents.
> `delete_document` permanently removes a document and all its annotations.
> Always double-check the `project_id` and `document_id` before calling these tools.
> INCEpTION does not provide an undo mechanism via the API.

The server runs locally and is only reachable from the machine where it is started.
Credentials are read from environment variables — never hard-code them in configuration
files that may be committed to version control. The `.gitignore` provided in this
repository excludes `.env` by default.

---

## INCEpTION API reference

The full AERO v1 Swagger UI is available at:

```
http://<your-inception-host>:<port>/swagger-ui.html
```

---

## License

[MIT](LICENSE) — you are free to use, modify, and redistribute this software in any project, commercial or not, as long as the original copyright notice is kept. You are not required to open-source your own code that uses this package.

In short: do whatever you want with it, just don't remove the licence header.
