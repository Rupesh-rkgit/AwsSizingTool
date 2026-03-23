"""SQLite database layer for session and report persistence.

Uses aiosqlite for async access from FastAPI.
"""

from __future__ import annotations

from datetime import datetime, timezone

import aiosqlite


class DatabaseManager:
    """Manages SQLite connection, schema creation, and CRUD operations.

    Uses a single persistent connection so that in-memory databases
    (`:memory:`) retain their schema across method calls.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    async def _get_conn(self) -> aiosqlite.Connection:
        """Return the existing connection or open a new one."""
        if self._conn is None:
            self._conn = await aiosqlite.connect(self.db_path)
            await self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def close(self) -> None:
        """Close the underlying connection if open."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        db = await self._get_conn()
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                prompt_text TEXT,
                region TEXT NOT NULL DEFAULT 'us-east-1',
                had_diagram INTEGER NOT NULL DEFAULT 0,
                diagram_filename TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT,
                total_monthly_cost REAL,
                bedrock_model_id TEXT,
                bedrock_latency_ms INTEGER
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                sizing_report_md TEXT,
                bom_md TEXT,
                html_report TEXT,
                report_data_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
            """
        )
        await db.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_created_at
            ON sessions(created_at DESC)
            """
        )
        await db.commit()

    async def create_session(
        self,
        session_id: str,
        prompt_text: str | None,
        region: str,
        had_diagram: bool,
        diagram_filename: str | None,
        bedrock_model_id: str | None,
    ) -> dict:
        """Insert a new session row and return it as a dict."""
        created_at = datetime.now(timezone.utc).isoformat()
        db = await self._get_conn()
        await db.execute(
            """
            INSERT INTO sessions
                (id, created_at, prompt_text, region, had_diagram,
                 diagram_filename, status, bedrock_model_id)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                session_id,
                created_at,
                prompt_text,
                region,
                1 if had_diagram else 0,
                diagram_filename,
                bedrock_model_id,
            ),
        )
        await db.commit()
        return {
            "id": session_id,
            "created_at": created_at,
            "prompt_text": prompt_text,
            "region": region,
            "had_diagram": had_diagram,
            "diagram_filename": diagram_filename,
            "status": "pending",
            "error_message": None,
            "total_monthly_cost": None,
            "bedrock_model_id": bedrock_model_id,
            "bedrock_latency_ms": None,
        }

    async def update_session_status(
        self,
        session_id: str,
        status: str,
        error_message: str | None = None,
        total_monthly_cost: float | None = None,
        bedrock_latency_ms: int | None = None,
    ) -> None:
        """Update a session's status and optional metadata fields."""
        db = await self._get_conn()
        await db.execute(
            """
            UPDATE sessions
            SET status = ?,
                error_message = ?,
                total_monthly_cost = ?,
                bedrock_latency_ms = ?
            WHERE id = ?
            """,
            (status, error_message, total_monthly_cost, bedrock_latency_ms, session_id),
        )
        await db.commit()

    async def get_session(self, session_id: str) -> dict | None:
        """Return a single session as a dict, or None if not found."""
        db = await self._get_conn()
        async with db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return _session_row_to_dict(row)

    async def list_sessions(
        self, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict], int]:
        """Return a page of completed sessions (most recent first) and total count.

        Only sessions with status='completed' are returned so that pending
        or failed analyses never appear in the user's history.
        """
        db = await self._get_conn()

        # Total count — completed only
        async with db.execute(
            "SELECT COUNT(*) FROM sessions WHERE status = 'completed'"
        ) as cursor:
            total = (await cursor.fetchone())[0]

        offset = (page - 1) * per_page
        async with db.execute(
            "SELECT * FROM sessions WHERE status = 'completed' "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (per_page, offset),
        ) as cursor:
            rows = await cursor.fetchall()

        sessions = [_session_row_to_dict(r) for r in rows]
        return sessions, total

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and its reports (via CASCADE). Return True if deleted."""
        db = await self._get_conn()
        cursor = await db.execute(
            "DELETE FROM sessions WHERE id = ?", (session_id,)
        )
        await db.commit()
        return cursor.rowcount > 0

    async def store_report(
        self,
        report_id: str,
        session_id: str,
        sizing_report_md: str | None,
        bom_md: str | None,
        html_report: str | None,
        report_data_json: str | None,
    ) -> None:
        """Insert a report row linked to a session."""
        db = await self._get_conn()
        await db.execute(
            """
            INSERT INTO reports
                (id, session_id, sizing_report_md, bom_md, html_report, report_data_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (report_id, session_id, sizing_report_md, bom_md, html_report, report_data_json),
        )
        await db.commit()

    async def get_report(self, session_id: str) -> dict | None:
        """Return the report for a given session, or None if not found."""
        db = await self._get_conn()
        async with db.execute(
            "SELECT * FROM reports WHERE session_id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return {
                "id": row["id"],
                "session_id": row["session_id"],
                "sizing_report_md": row["sizing_report_md"],
                "bom_md": row["bom_md"],
                "html_report": row["html_report"],
                "report_data_json": row["report_data_json"],
            }


def _session_row_to_dict(row: aiosqlite.Row) -> dict:
    """Convert a session Row to a plain dict with proper types."""
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "prompt_text": row["prompt_text"],
        "region": row["region"],
        "had_diagram": bool(row["had_diagram"]),
        "diagram_filename": row["diagram_filename"],
        "status": row["status"],
        "error_message": row["error_message"],
        "total_monthly_cost": row["total_monthly_cost"],
        "bedrock_model_id": row["bedrock_model_id"],
        "bedrock_latency_ms": row["bedrock_latency_ms"],
    }
