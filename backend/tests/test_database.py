"""Unit tests for DatabaseManager using in-memory SQLite."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio

from backend.services.database import DatabaseManager


@pytest_asyncio.fixture
async def db():
    """Create an in-memory DatabaseManager with schema initialized."""
    manager = DatabaseManager(":memory:")
    await manager.init_db()
    yield manager
    await manager.close()


def _new_id() -> str:
    return str(uuid.uuid4())


# ── Schema creation ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_init_db_creates_tables(db: DatabaseManager):
    """init_db should create sessions and reports tables."""
    conn = await db._get_conn()
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ) as cur:
        tables = [row[0] for row in await cur.fetchall()]
    assert "sessions" in tables
    assert "reports" in tables


@pytest.mark.asyncio
async def test_init_db_creates_index(db: DatabaseManager):
    """init_db should create the created_at descending index."""
    conn = await db._get_conn()
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'"
    ) as cur:
        indexes = [row[0] for row in await cur.fetchall()]
    assert "idx_sessions_created_at" in indexes


@pytest.mark.asyncio
async def test_init_db_idempotent(db: DatabaseManager):
    """Calling init_db twice should not raise."""
    await db.init_db()


# ── Session CRUD ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session_returns_dict(db: DatabaseManager):
    sid = _new_id()
    result = await db.create_session(
        session_id=sid,
        prompt_text="size my app",
        region="us-west-2",
        had_diagram=True,
        diagram_filename="arch.png",
        bedrock_model_id="anthropic.claude-3-5-sonnet",
    )
    assert result["id"] == sid
    assert result["prompt_text"] == "size my app"
    assert result["region"] == "us-west-2"
    assert result["had_diagram"] is True
    assert result["diagram_filename"] == "arch.png"
    assert result["status"] == "pending"
    assert result["error_message"] is None
    assert result["total_monthly_cost"] is None
    assert result["bedrock_model_id"] == "anthropic.claude-3-5-sonnet"


@pytest.mark.asyncio
async def test_get_session_found(db: DatabaseManager):
    sid = _new_id()
    await db.create_session(sid, "prompt", "us-east-1", False, None, None)
    session = await db.get_session(sid)
    assert session is not None
    assert session["id"] == sid
    assert session["had_diagram"] is False


@pytest.mark.asyncio
async def test_get_session_not_found(db: DatabaseManager):
    result = await db.get_session("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_update_session_status(db: DatabaseManager):
    sid = _new_id()
    await db.create_session(sid, None, "us-east-1", False, None, None)
    await db.update_session_status(
        sid, "completed", total_monthly_cost=1234.56, bedrock_latency_ms=800
    )
    session = await db.get_session(sid)
    assert session["status"] == "completed"
    assert session["total_monthly_cost"] == pytest.approx(1234.56)
    assert session["bedrock_latency_ms"] == 800
    assert session["error_message"] is None


@pytest.mark.asyncio
async def test_update_session_status_failed(db: DatabaseManager):
    sid = _new_id()
    await db.create_session(sid, None, "us-east-1", False, None, None)
    await db.update_session_status(sid, "failed", error_message="timeout")
    session = await db.get_session(sid)
    assert session["status"] == "failed"
    assert session["error_message"] == "timeout"


# ── List sessions (paginated, most recent first) ────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_empty(db: DatabaseManager):
    sessions, total = await db.list_sessions()
    assert sessions == []
    assert total == 0


@pytest.mark.asyncio
async def test_list_sessions_ordering_and_pagination(db: DatabaseManager):
    """Sessions should come back most-recent-first with correct pagination."""
    ids = []
    for i in range(5):
        sid = _new_id()
        ids.append(sid)
        await db.create_session(sid, f"prompt {i}", "us-east-1", False, None, None)

    # Page 1, 2 per page
    page1, total = await db.list_sessions(page=1, per_page=2)
    assert total == 5
    assert len(page1) == 2

    # Page 2
    page2, _ = await db.list_sessions(page=2, per_page=2)
    assert len(page2) == 2

    # Page 3 (last)
    page3, _ = await db.list_sessions(page=3, per_page=2)
    assert len(page3) == 1

    # Most recent first: created_at should be descending
    all_sessions = page1 + page2 + page3
    timestamps = [s["created_at"] for s in all_sessions]
    assert timestamps == sorted(timestamps, reverse=True)


# ── Delete session (cascade) ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_session_returns_true(db: DatabaseManager):
    sid = _new_id()
    await db.create_session(sid, None, "us-east-1", False, None, None)
    assert await db.delete_session(sid) is True
    assert await db.get_session(sid) is None


@pytest.mark.asyncio
async def test_delete_session_not_found(db: DatabaseManager):
    assert await db.delete_session("nonexistent") is False


@pytest.mark.asyncio
async def test_delete_session_cascades_to_reports(db: DatabaseManager):
    sid = _new_id()
    rid = _new_id()
    await db.create_session(sid, None, "us-east-1", False, None, None)
    await db.store_report(rid, sid, "md", "bom", "<html>", '{"key":"val"}')
    assert await db.get_report(sid) is not None

    await db.delete_session(sid)
    assert await db.get_report(sid) is None


# ── Report storage and retrieval ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_store_and_get_report(db: DatabaseManager):
    sid = _new_id()
    rid = _new_id()
    await db.create_session(sid, None, "us-east-1", False, None, None)
    await db.store_report(rid, sid, "# Sizing", "# BOM", "<h1>Report</h1>", '{}')

    report = await db.get_report(sid)
    assert report is not None
    assert report["id"] == rid
    assert report["session_id"] == sid
    assert report["sizing_report_md"] == "# Sizing"
    assert report["bom_md"] == "# BOM"
    assert report["html_report"] == "<h1>Report</h1>"
    assert report["report_data_json"] == "{}"


@pytest.mark.asyncio
async def test_get_report_not_found(db: DatabaseManager):
    result = await db.get_report("nonexistent")
    assert result is None
