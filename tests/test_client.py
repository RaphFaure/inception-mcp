"""
Tests unitaires pour InceptionClient.

Stratégie : mock de requests.get / requests.post / requests.delete
→ aucun serveur INCEpTION requis.

Lancement :
    pip install pytest
    pytest tests/
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from inception_mcp.client import InceptionClient, InceptionError

BASE = "http://localhost:8080"
AUTH = ("admin", "password")
CLIENT = InceptionClient(BASE, *AUTH)


def _mock_response(body=None, messages=None, status=200, content_type="application/json",
                   raw_content=None):
    """Fabrique un mock de requests.Response."""
    m = MagicMock()
    m.status_code = status
    m.headers = {"Content-Type": content_type}
    payload = {"messages": messages or [], "body": body}
    m.json.return_value = payload
    m.text = json.dumps(payload)
    m.content = raw_content or json.dumps(payload).encode()
    return m


def _mock_error(message="Internal server error", status=500):
    m = MagicMock()
    m.status_code = status
    m.headers = {"Content-Type": "application/json"}
    payload = {"messages": [{"level": "ERROR", "message": message}], "body": None}
    m.json.return_value = payload
    m.text = json.dumps(payload)
    m.content = json.dumps(payload).encode()
    return m


# ------------------------------------------------------------------
# Projects
# ------------------------------------------------------------------

class TestProjects:

    def test_list_projects(self):
        projects = [{"id": 1, "name": "db_narratives"}]
        with patch("requests.get", return_value=_mock_response(projects)):
            result = CLIENT.list_projects()
        assert result == projects

    def test_list_projects_empty(self):
        with patch("requests.get", return_value=_mock_response(None)):
            result = CLIENT.list_projects()
        assert result == []

    def test_create_project(self):
        project = {"id": 2, "name": "test_project"}
        with patch("requests.post", return_value=_mock_response(project)):
            result = CLIENT.create_project("test_project", "A test")
        assert result["id"] == 2
        assert result["name"] == "test_project"

    def test_delete_project(self):
        with patch("requests.delete", return_value=_mock_response(None)):
            CLIENT.delete_project(1)  # Should not raise

    def test_export_project_zip(self):
        zip_bytes = b"PK\x03\x04fake_zip_content"
        mock = MagicMock()
        mock.status_code = 200
        mock.headers = {"Content-Type": "application/zip"}
        mock.content = zip_bytes
        mock.json.side_effect = Exception("not JSON")
        with patch("requests.get", return_value=mock):
            result = CLIENT.export_project_zip(1)
        assert result == zip_bytes

    def test_import_project_zip(self, tmp_path):
        zip_file = tmp_path / "project.zip"
        zip_file.write_bytes(b"PK\x03\x04fake")
        project = {"id": 3, "name": "imported"}
        with patch("requests.post", return_value=_mock_response(project)):
            result = CLIENT.import_project_zip(zip_file)
        assert result["name"] == "imported"

    def test_project_status(self):
        docs = [{"id": 1, "name": "doc.txt", "state": "NEW"}]
        annots = [{"user": "admin", "state": "IN_PROGRESS"}]
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _mock_response(docs),    # list_documents
                _mock_response(annots),  # list_annotations for doc 1
            ]
            result = CLIENT.project_status(1)
        assert result["n_documents"] == 1
        assert result["documents"][0]["name"] == "doc.txt"
        assert result["documents"][0]["annotators"][0]["user"] == "admin"


# ------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------

class TestDocuments:

    def test_list_documents(self):
        docs = [{"id": 1, "name": "doc.txt", "state": "NEW"}]
        with patch("requests.get", return_value=_mock_response(docs)):
            result = CLIENT.list_documents(1)
        assert len(result) == 1
        assert result[0]["name"] == "doc.txt"

    def test_upload_document_str(self):
        doc = {"id": 5, "name": "test.txt", "state": "NEW"}
        with patch("requests.post", return_value=_mock_response(doc)) as mock_post:
            result = CLIENT.upload_document(1, "test.txt", "Hello world")
        assert result["id"] == 5
        call_kwargs = mock_post.call_args
        # Verify the encoded content was actually passed in the files argument
        files_arg = call_kwargs.kwargs.get("files") or call_kwargs[1].get("files")
        assert files_arg is not None, "No files argument found in POST call"
        file_content = files_arg["content"][1]
        assert file_content == b"Hello world"

    def test_upload_document_from_file(self, tmp_path):
        doc_file = tmp_path / "sample.txt"
        doc_file.write_text("Sample content")
        doc = {"id": 6, "name": "sample.txt", "state": "NEW"}
        with patch("requests.post", return_value=_mock_response(doc)):
            result = CLIENT.upload_document_from_file(1, doc_file)
        assert result["name"] == "sample.txt"

    def test_batch_upload(self, tmp_path):
        (tmp_path / "a.txt").write_text("A")
        (tmp_path / "b.txt").write_text("B")
        (tmp_path / "skip.csv").write_text("skip")
        doc = {"id": 7, "name": "a.txt", "state": "NEW"}
        with patch("requests.post", return_value=_mock_response(doc)):
            results = CLIENT.batch_upload(1, tmp_path, glob="*.txt")
        assert len(results) == 2

    def test_export_document_source(self):
        text_bytes = b"Once upon a time..."
        mock = MagicMock()
        mock.status_code = 200
        mock.headers = {"Content-Type": "text/plain"}
        mock.content = text_bytes
        mock.json.side_effect = Exception("not JSON")
        with patch("requests.get", return_value=mock):
            result = CLIENT.export_document_source(1, 1)
        assert result == text_bytes

    def test_delete_document(self):
        with patch("requests.delete", return_value=_mock_response(None)):
            CLIENT.delete_document(1, 1)  # Should not raise


# ------------------------------------------------------------------
# Annotations
# ------------------------------------------------------------------

class TestAnnotations:

    def test_list_annotations(self):
        annots = [{"user": "admin", "state": "IN_PROGRESS"}]
        with patch("requests.get", return_value=_mock_response(annots)):
            result = CLIENT.list_annotations(1, 1)
        assert result[0]["user"] == "admin"

    def test_export_annotations(self):
        tsv_bytes = b"#FORMAT=WebAnno TSV 3.3\n"
        mock = MagicMock()
        mock.status_code = 200
        mock.headers = {"Content-Type": "text/plain"}
        mock.content = tsv_bytes
        mock.json.side_effect = Exception("not JSON")
        with patch("requests.get", return_value=mock):
            result = CLIENT.export_annotations(1, 1, "admin", "ctsv3")
        assert result == tsv_bytes

    def test_export_all_annotations(self, tmp_path):
        docs = [
            {"id": 1, "name": "doc1.txt", "state": "NEW"},
            {"id": 2, "name": "doc2.txt", "state": "NEW"},
        ]
        tsv_bytes = b"#FORMAT=WebAnno TSV 3.3\n"
        mock_bin = MagicMock()
        mock_bin.status_code = 200
        mock_bin.headers = {"Content-Type": "text/plain"}
        mock_bin.content = tsv_bytes
        mock_bin.json.side_effect = Exception("not JSON")

        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _mock_response(docs),  # list_documents
                mock_bin,              # export doc 1
                mock_bin,              # export doc 2
            ]
            results = CLIENT.export_all_annotations(1, "admin", tmp_path)
        assert len(results) == 2
        assert all(r["ok"] for r in results)
        assert (tmp_path / "doc1.ctsv3").exists()

    def test_delete_annotations(self):
        with patch("requests.delete", return_value=_mock_response(None)):
            CLIENT.delete_annotations(1, 1, "admin")  # Should not raise

    def test_import_annotations(self):
        with patch("requests.post", return_value=_mock_response(None)):
            CLIENT.import_annotations(1, 1, "admin", b"fake content")


# ------------------------------------------------------------------
# Curation
# ------------------------------------------------------------------

class TestCuration:

    def test_export_curation(self):
        tsv_bytes = b"#FORMAT=WebAnno TSV 3.3\ncurated content\n"
        mock = MagicMock()
        mock.status_code = 200
        mock.headers = {"Content-Type": "text/plain"}
        mock.content = tsv_bytes
        mock.json.side_effect = Exception("not JSON")
        with patch("requests.get", return_value=mock):
            result = CLIENT.export_curation(1, 1)
        assert result == tsv_bytes

    def test_delete_curation(self):
        with patch("requests.delete", return_value=_mock_response(None)):
            CLIENT.delete_curation(1, 1)  # Should not raise


# ------------------------------------------------------------------
# Error handling
# ------------------------------------------------------------------

class TestErrors:

    def test_api_error_raises(self):
        with patch("requests.get", return_value=_mock_error("Not found", 404)):
            with pytest.raises(InceptionError, match="Not found"):
                CLIENT.list_projects()

    def test_non_json_response_raises(self):
        mock = MagicMock()
        mock.status_code = 200
        mock.headers = {"Content-Type": "text/html"}
        mock.json.side_effect = Exception("not JSON")
        mock.text = "<html>error</html>"
        with patch("requests.get", return_value=mock):
            with pytest.raises(InceptionError):
                CLIENT.list_projects()
