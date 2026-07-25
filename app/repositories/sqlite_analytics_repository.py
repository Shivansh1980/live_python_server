import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.domain.analytics import (
    AnalyticsEvent,
    AnalyticsEventType,
    NewAnalyticsEvent,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO app_settings (key, value, updated_at)
VALUES ('analytics_recording_enabled', 'true', CURRENT_TIMESTAMP);

CREATE TABLE IF NOT EXISTS analytics_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    page_url TEXT NOT NULL,
    page_title TEXT NOT NULL DEFAULT '',
    section TEXT NOT NULL DEFAULT '',
    element_tag TEXT NOT NULL DEFAULT '',
    element_id TEXT NOT NULL DEFAULT '',
    element_label TEXT NOT NULL DEFAULT '',
    duration_ms INTEGER,
    scroll_depth REAL,
    pointer_x REAL,
    pointer_y REAL,
    viewport_width INTEGER,
    viewport_height INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    user_agent TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_analytics_created_at
    ON analytics_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analytics_session_id
    ON analytics_events(session_id);
CREATE INDEX IF NOT EXISTS idx_analytics_event_type
    ON analytics_events(event_type);
"""


class SQLiteAnalyticsRepository:
    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.executescript(SCHEMA)
            connection.commit()

    def is_recording_enabled(self) -> bool:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT value
                FROM app_settings
                WHERE key = 'analytics_recording_enabled'
                """
            ).fetchone()
        return bool(row and str(row["value"]).casefold() == "true")

    def set_recording_enabled(self, enabled: bool) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO app_settings (key, value, updated_at)
                VALUES ('analytics_recording_enabled', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
                """,
                (
                    "true" if enabled else "false",
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()

    def create(self, event: NewAnalyticsEvent) -> AnalyticsEvent | None:
        created_at = datetime.now(timezone.utc)
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            setting = connection.execute(
                """
                SELECT value
                FROM app_settings
                WHERE key = 'analytics_recording_enabled'
                """
            ).fetchone()
            if not setting or str(setting["value"]).casefold() != "true":
                connection.rollback()
                return None
            cursor = connection.execute(
                """
                INSERT INTO analytics_events (
                    session_id, event_type, page_url, page_title, section,
                    element_tag, element_id, element_label, duration_ms,
                    scroll_depth, pointer_x, pointer_y, viewport_width,
                    viewport_height, metadata_json, user_agent, occurred_at,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.event_type.value,
                    event.page_url,
                    event.page_title,
                    event.section,
                    event.element_tag,
                    event.element_id,
                    event.element_label,
                    event.duration_ms,
                    event.scroll_depth,
                    event.pointer_x,
                    event.pointer_y,
                    event.viewport_width,
                    event.viewport_height,
                    event.metadata_json,
                    event.user_agent,
                    event.occurred_at.isoformat(),
                    created_at.isoformat(),
                ),
            )
            event_id = int(cursor.lastrowid)
            connection.commit()
        stored = self.get(event_id)
        if stored is None:
            raise RuntimeError("Stored analytics event could not be reloaded.")
        return stored

    def get(self, event_id: int) -> AnalyticsEvent | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM analytics_events WHERE id = ?",
                (event_id,),
            ).fetchone()
        return self._to_event(row) if row else None

    def list(
        self,
        *,
        search: str = "",
        event_type: AnalyticsEventType | None = None,
        limit: int = 200,
    ) -> list[AnalyticsEvent]:
        clauses: list[str] = []
        parameters: list[object] = []
        if search:
            clauses.append(
                """
                (
                    session_id LIKE ? OR page_url LIKE ? OR section LIKE ?
                    OR element_label LIKE ?
                )
                """
            )
            term = f"%{search}%"
            parameters.extend([term, term, term, term])
        if event_type is not None:
            clauses.append("event_type = ?")
            parameters.append(event_type.value)
        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(limit, 500)))
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM analytics_events
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [self._to_event(row) for row in rows]

    def summary(self) -> dict[str, object]:
        with self._connection() as connection:
            totals = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(DISTINCT session_id) AS sessions,
                    COALESCE(AVG(duration_ms), 0) AS average_duration,
                    COALESCE(AVG(scroll_depth), 0) AS average_scroll
                FROM analytics_events
                """
            ).fetchone()
            types = connection.execute(
                """
                SELECT event_type, COUNT(*) AS count
                FROM analytics_events
                GROUP BY event_type
                ORDER BY count DESC, event_type
                LIMIT 8
                """
            ).fetchall()
            pages = connection.execute(
                """
                SELECT page_url, COUNT(*) AS count
                FROM analytics_events
                GROUP BY page_url
                ORDER BY count DESC, page_url
                LIMIT 8
                """
            ).fetchall()
            sections = connection.execute(
                """
                SELECT section, COUNT(*) AS count
                FROM analytics_events
                WHERE section != ''
                GROUP BY section
                ORDER BY count DESC, section
                LIMIT 8
                """
            ).fetchall()
        return {
            "total": int(totals["total"]),
            "sessions": int(totals["sessions"]),
            "average_duration_ms": int(totals["average_duration"]),
            "average_scroll": round(float(totals["average_scroll"]), 1),
            "event_types": [
                {"name": str(row["event_type"]), "count": int(row["count"])}
                for row in types
            ],
            "pages": [
                {"name": str(row["page_url"]), "count": int(row["count"])}
                for row in pages
            ],
            "sections": [
                {"name": str(row["section"]), "count": int(row["count"])}
                for row in sections
            ],
        }

    def delete(self, event_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM analytics_events WHERE id = ?",
                (event_id,),
            )
            connection.commit()
        return cursor.rowcount > 0

    def delete_all(self) -> int:
        with self._connection() as connection:
            cursor = connection.execute("DELETE FROM analytics_events")
            connection.commit()
        return cursor.rowcount

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self._database_path,
            timeout=10,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
        finally:
            connection.close()

    @staticmethod
    def _to_event(row: sqlite3.Row) -> AnalyticsEvent:
        return AnalyticsEvent(
            id=int(row["id"]),
            session_id=str(row["session_id"]),
            event_type=AnalyticsEventType(str(row["event_type"])),
            page_url=str(row["page_url"]),
            page_title=str(row["page_title"]),
            section=str(row["section"]),
            element_tag=str(row["element_tag"]),
            element_id=str(row["element_id"]),
            element_label=str(row["element_label"]),
            duration_ms=(
                int(row["duration_ms"])
                if row["duration_ms"] is not None
                else None
            ),
            scroll_depth=(
                float(row["scroll_depth"])
                if row["scroll_depth"] is not None
                else None
            ),
            pointer_x=(
                float(row["pointer_x"])
                if row["pointer_x"] is not None
                else None
            ),
            pointer_y=(
                float(row["pointer_y"])
                if row["pointer_y"] is not None
                else None
            ),
            viewport_width=(
                int(row["viewport_width"])
                if row["viewport_width"] is not None
                else None
            ),
            viewport_height=(
                int(row["viewport_height"])
                if row["viewport_height"] is not None
                else None
            ),
            metadata_json=str(row["metadata_json"]),
            user_agent=str(row["user_agent"]),
            occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
