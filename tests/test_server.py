"""
Smoke tests for the MCP server.

Verifies that all 18 expected MCP tools are registered in the FastMCP instance.
No INCEpTION server required.
"""

from __future__ import annotations

from inception_mcp.server import mcp

EXPECTED_TOOLS = [
    "list_projects",
    "create_project",
    "delete_project",
    "export_project_zip",
    "import_project_zip",
    "project_status",
    "list_documents",
    "upload_document",
    "batch_upload",
    "export_document_source",
    "delete_document",
    "list_annotations",
    "export_annotations",
    "export_all_annotations",
    "import_annotations",
    "delete_annotations",
    "export_curation",
    "delete_curation",
]


def test_all_18_tools_registered():
    """All 18 MCP tools must be registered in the FastMCP instance."""
    import asyncio

    tools = asyncio.run(mcp.list_tools())
    registered_names = {t.name for t in tools}
    for tool_name in EXPECTED_TOOLS:
        assert tool_name in registered_names, (
            f"MCP tool '{tool_name}' is not registered. "
            f"Registered tools: {sorted(registered_names)}"
        )
    assert len(registered_names) == len(EXPECTED_TOOLS), (
        f"Expected {len(EXPECTED_TOOLS)} tools, found {len(registered_names)}: "
        f"{sorted(registered_names)}"
    )
