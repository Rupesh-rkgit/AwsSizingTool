"""Tests for session history endpoints: GET /api/sessions, GET /api/sessions/{id}, DELETE /api/sessions/{id}."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixture: TestClient with mocked services
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    """TestClient with all backend services mocked out."""
    import backend.main as main_mod

    @asynccontextmanager
    async def _noop_lifespan(app):
        yield

    original_lifespan = main_mod.app.router.lifespan_context
    main_mod.app.router.lifespan_context = _noop_lifespan

    mock_settings = MagicMock()
    mock_settings.bedrock.model_id = "test-model"

    main_mod._settings = mock_settings
    main_mod._input_validator = MagicMock()
    main_mod._sizing_engine = MagicMock()
    main_mod._report_generator = MagicMock()
    main_mod._db_manager = MagicMock()
    main_mod._db_manager.list_sessions = AsyncMock()
    main_mod._db_manager.get_session = AsyncMock()
    main_mod._db_manager.get_report = AsyncMock()
    main_mod._db_manager.delete_session = AsyncMock()

    with TestClient(main_mod.app, raise_server_exceptions=False) as c:
        yield c, main_mod

    main_mod.app.router.lifespan_context = original_lifespan


# ---------------------------------------------------------------------------
# GET /api/sessions
# ---------------------------------------------------------------------------


class TestListSessions:

    def test_returns_paginated_sessions(self, client):
        c, mod = client
        mod._db_manager.list_sessions.return_value = (
            [
                {
                    "id": "abc-123",
                    "created_at": "2025-01-15T00:00:00+00:00",
                    "prompt_text": "Size my infrastructure for a web app",
                    "region": "us-east-1",
                    "had_diagram": True,
                    "diagram_filename": "arch.png",
                    "status": "completed",
                    "error_message": None,
                    "total_monthly_cost": 1538.93,
                    "bedrock_model_id": "test-model",
                    "bedrock_latency_ms": 5000,
                },
            ],
            1,
        )

        resp = c.get("/api/sessions?page=1&per_page=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["page"] == 1
        assert body["per_page"] == 10
        assert len(body["sessions"]) == 1

        session = body["sessions"][0]
        assert session["id"] == "abc-123"
        assert session["prompt_snippet"] == "Size my infrastructure for a web app"
        assert session["region"] == "us-east-1"
        assert session["had_diagram"] is True
        assert session["total_monthly_cost"] == 1538.93

    def test_prompt_snippet_truncated_to_100_chars(self, client):
        c, mod = client
        long_prompt = "A" * 200
        mod._db_manager.list_sessions.return_value = (
            [
                {
                    "id": "abc-456",
                    "created_at": "2025-01-15T00:00:00+00:00",
                    "prompt_text": long_prompt,
                    "region": "us-east-1",
                    "had_diagram": False,
                    "diagram_filename": None,
                    "status": "completed",
                    "error_message": None,
                    "total_monthly_cost": 100.0,
                    "bedrock_model_id": "test-model",
                    "bedrock_latency_ms": 3000,
                },
            ],
            1,
        )

        resp = c.get("/api/sessions")
        body = resp.json()
        assert len(body["sessions"][0]["prompt_snippet"]) == 100

    def test_null_prompt_text_returns_empty_snippet(self, client):
        c, mod = client
        mod._db_manager.list_sessions.return_value = (
            [
                {
                    "id": "abc-789",
                    "created_at": "2025-01-15T00:00:00+00:00",
                    "prompt_text": None,
                    "region": "us-east-1",
                    "had_diagram": True,
                    "diagram_filename": "arch.png",
                    "status": "completed",
                    "error_message": None,
                    "total_monthly_cost": 500.0,
                    "bedrock_model_id": "test-model",
                    "bedrock_latency_ms": 2000,
                },
            ],
            1,
        )

        resp = c.get("/api/sessions")
        body = resp.json()
        assert body["sessions"][0]["prompt_snippet"] == ""

    def test_empty_sessions_list(self, client):
        c, mod = client
        mod._db_manager.list_sessions.return_value = ([], 0)

        resp = c.get("/api/sessions")
        assert resp.status_code == 200
        body = resp.json()
        assert body["sessions"] == []
        assert body["total"] == 0

    def test_default_pagination_params(self, client):
        c, mod = client
        mod._db_manager.list_sessions.return_value = ([], 0)

        c.get("/api/sessions")
        mod._db_manager.list_sessions.assert_called_once_with(page=1, per_page=20)


# ---------------------------------------------------------------------------
# GET /api/sessions/{id}
# ---------------------------------------------------------------------------


class TestGetSession:

    def test_returns_full_report_artifacts(self, client):
        c, mod = client
        mod._db_manager.get_session.return_value = {
            "id": "sess-001",
            "created_at": "2025-01-15T00:00:00+00:00",
            "prompt_text": "Size my infra",
            "region": "us-east-1",
            "had_diagram": False,
            "status": "completed",
        }
        mod._db_manager.get_report.return_value = {
            "id": "rpt-001",
            "session_id": "sess-001",
            "sizing_report_md": "# Sizing Report",
            "bom_md": "# BOM",
            "html_report": "<html>report</html>",
            "report_data_json": '{"test": "json"}',
        }

        resp = c.get("/api/sessions/sess-001")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "sess-001"
        assert body["sizing_report_md"] == "# Sizing Report"
        assert body["bom_md"] == "# BOM"
        assert body["html_report"] == "<html>report</html>"
        assert body["report_data_json"] == '{"test": "json"}'
        assert body["generated_at"] == "2025-01-15T00:00:00+00:00"

    def test_session_not_found_returns_404(self, client):
        c, mod = client
        mod._db_manager.get_session.return_value = None

        resp = c.get("/api/sessions/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["error"] == "Session not found"

    def test_session_without_report_returns_nulls(self, client):
        c, mod = client
        mod._db_manager.get_session.return_value = {
            "id": "sess-002",
            "created_at": "2025-01-15T00:00:00+00:00",
            "prompt_text": "test",
            "region": "us-east-1",
            "had_diagram": False,
            "status": "failed",
        }
        mod._db_manager.get_report.return_value = None

        resp = c.get("/api/sessions/sess-002")
        assert resp.status_code == 200
        body = resp.json()
        assert body["session_id"] == "sess-002"
        assert body["sizing_report_md"] is None
        assert body["bom_md"] is None
        assert body["html_report"] is None
        assert body["report_data_json"] is None


# ---------------------------------------------------------------------------
# DELETE /api/sessions/{id}
# ---------------------------------------------------------------------------


class TestDeleteSession:

    def test_successful_delete_returns_204(self, client):
        c, mod = client
        mod._db_manager.delete_session.return_value = True

        resp = c.delete("/api/sessions/sess-001")
        assert resp.status_code == 204
        assert resp.content == b""

    def test_delete_not_found_returns_404(self, client):
        c, mod = client
        mod._db_manager.delete_session.return_value = False

        resp = c.delete("/api/sessions/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["error"] == "Session not found"
