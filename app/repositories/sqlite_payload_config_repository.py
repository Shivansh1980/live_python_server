import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.domain.payload_config import NewPayloadConfig, PayloadConfig

TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS payload_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    should_replace_payload INTEGER NOT NULL DEFAULT 0
        CHECK (should_replace_payload IN (0, 1)),
    remote_host TEXT,
    remote_port INTEGER
        CHECK (remote_port IS NULL OR remote_port BETWEEN 1 AND 65535),
    user_ip_address TEXT,
    user_host_name TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

INDEX_SCHEMA = """
CREATE INDEX IF NOT EXISTS idx_payload_configs_ip_active_latest
    ON payload_configs(user_ip_address, is_active, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_payload_configs_updated_at
    ON payload_configs(updated_at DESC);
"""


class SQLitePayloadConfigRepository:
    """SQLite-backed payload configuration persistence."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = database_path
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(TABLE_SCHEMA)
            self._migrate_payload_config_schema(connection)
            connection.executescript(INDEX_SCHEMA)
            connection.commit()

    def create(self, payload_config: NewPayloadConfig) -> PayloadConfig:
        now = datetime.now(timezone.utc)
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO payload_configs (
                    should_replace_payload, remote_host, remote_port,
                    user_ip_address, user_host_name, is_active, created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(payload_config.should_replace_payload),
                    payload_config.remote_host,
                    payload_config.remote_port,
                    payload_config.user_ip_address,
                    payload_config.user_host_name,
                    int(payload_config.is_active),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            payload_config_id = int(cursor.lastrowid)
            connection.commit()
        stored = self.get(payload_config_id)
        if stored is None:
            raise RuntimeError("Stored payload configuration could not be reloaded.")
        return stored

    def get(self, payload_config_id: int) -> PayloadConfig | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM payload_configs WHERE id = ?",
                (payload_config_id,),
            ).fetchone()
        return self._to_payload_config(row) if row else None

    def get_latest_active_by_ip(
        self,
        user_ip_address: str,
    ) -> PayloadConfig | None:
        with self._connection() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM payload_configs
                WHERE user_ip_address = ? AND is_active = 1
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (user_ip_address,),
            ).fetchone()
        return self._to_payload_config(row) if row else None

    def list(
        self,
        *,
        search: str = "",
        limit: int = 200,
    ) -> list[PayloadConfig]:
        parameters: list[object] = []
        where_clause = ""
        if search:
            where_clause = """
                WHERE user_ip_address LIKE ? OR user_host_name LIKE ?
                    OR remote_host LIKE ?
            """
            term = f"%{search}%"
            parameters.extend([term, term, term])
        parameters.append(max(1, min(limit, 500)))
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM payload_configs
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [self._to_payload_config(row) for row in rows]

    def update(
        self,
        payload_config_id: int,
        payload_config: NewPayloadConfig,
    ) -> PayloadConfig | None:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE payload_configs
                SET should_replace_payload = ?, remote_host = ?,
                    remote_port = ?, user_ip_address = ?, user_host_name = ?,
                    is_active = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    int(payload_config.should_replace_payload),
                    payload_config.remote_host,
                    payload_config.remote_port,
                    payload_config.user_ip_address,
                    payload_config.user_host_name,
                    int(payload_config.is_active),
                    datetime.now(timezone.utc).isoformat(),
                    payload_config_id,
                ),
            )
            connection.commit()
        return self.get(payload_config_id) if cursor.rowcount else None

    def update_partial(
        self,
        payload_config_id: int,
        changes: dict[str, object],
    ) -> PayloadConfig | None:
        allowed_columns = {
            "should_replace_payload",
            "remote_host",
            "remote_port",
            "user_ip_address",
            "user_host_name",
            "is_active",
        }
        normalized_changes = {
            key: (
                int(value)
                if key in {"should_replace_payload", "is_active"}
                else value
            )
            for key, value in changes.items()
            if key in allowed_columns
        }
        if not normalized_changes:
            return self.get(payload_config_id)
        normalized_changes["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        assignments = ", ".join(
            f"{column} = ?" for column in normalized_changes
        )
        parameters = [*normalized_changes.values(), payload_config_id]
        with self._connection() as connection:
            cursor = connection.execute(
                f"""
                UPDATE payload_configs
                SET {assignments}
                WHERE id = ?
                """,
                parameters,
            )
            connection.commit()
        return self.get(payload_config_id) if cursor.rowcount else None

    def update_should_replace_for_latest_active(
        self,
        user_ip_address: str,
        should_replace_payload: bool,
    ) -> PayloadConfig | None:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT id
                FROM payload_configs
                WHERE user_ip_address = ? AND is_active = 1
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (user_ip_address,),
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            payload_config_id = int(row["id"])
            cursor = connection.execute(
                """
                UPDATE payload_configs
                SET should_replace_payload = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    int(should_replace_payload),
                    datetime.now(timezone.utc).isoformat(),
                    payload_config_id,
                ),
            )
            connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get(payload_config_id)

    def update_should_replace_for_latest_active_hostname(
        self,
        user_host_name: str,
        should_replace_payload: bool,
    ) -> PayloadConfig | None:
        with self._connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT id
                FROM payload_configs
                WHERE user_host_name = ? COLLATE NOCASE AND is_active = 1
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (user_host_name,),
            ).fetchone()
            if row is None:
                connection.rollback()
                return None
            payload_config_id = int(row["id"])
            cursor = connection.execute(
                """
                UPDATE payload_configs
                SET should_replace_payload = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    int(should_replace_payload),
                    datetime.now(timezone.utc).isoformat(),
                    payload_config_id,
                ),
            )
            connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get(payload_config_id)

    def update_should_replace_for_all(
        self,
        should_replace_payload: bool,
    ) -> int:
        with self._connection() as connection:
            cursor = connection.execute(
                """
                UPDATE payload_configs
                SET should_replace_payload = ?, updated_at = ?
                """,
                (
                    int(should_replace_payload),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.commit()
        return cursor.rowcount

    def delete(self, payload_config_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM payload_configs WHERE id = ?",
                (payload_config_id,),
            )
            connection.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _migrate_payload_config_schema(
        connection: sqlite3.Connection,
    ) -> None:
        columns = {
            str(row["name"]): row
            for row in connection.execute(
                "PRAGMA table_info(payload_configs)"
            ).fetchall()
        }
        nullable_columns = (
            "remote_host",
            "remote_port",
            "user_ip_address",
            "user_host_name",
        )
        requires_rebuild = "url" in columns or any(
            bool(columns[name]["notnull"])
            for name in nullable_columns
            if name in columns
        )
        if not requires_rebuild:
            return

        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "DROP INDEX IF EXISTS idx_payload_configs_ip_active_latest"
        )
        connection.execute(
            "DROP INDEX IF EXISTS idx_payload_configs_updated_at"
        )
        connection.execute(
            """
            ALTER TABLE payload_configs
            RENAME TO payload_configs_before_nullable_fields
            """
        )
        connection.execute(TABLE_SCHEMA)
        connection.execute(
            """
            INSERT INTO payload_configs (
                id, should_replace_payload, remote_host, remote_port,
                user_ip_address, user_host_name, is_active, created_at,
                updated_at
            )
            SELECT
                id, should_replace_payload, remote_host, remote_port,
                user_ip_address, user_host_name, is_active, created_at,
                updated_at
            FROM payload_configs_before_nullable_fields
            """
        )
        connection.execute(
            "DROP TABLE payload_configs_before_nullable_fields"
        )
        connection.commit()

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
    def _to_payload_config(row: sqlite3.Row) -> PayloadConfig:
        return PayloadConfig(
            id=int(row["id"]),
            should_replace_payload=bool(row["should_replace_payload"]),
            remote_host=(
                str(row["remote_host"])
                if row["remote_host"] is not None
                else None
            ),
            remote_port=(
                int(row["remote_port"])
                if row["remote_port"] is not None
                else None
            ),
            user_ip_address=(
                str(row["user_ip_address"])
                if row["user_ip_address"] is not None
                else None
            ),
            user_host_name=(
                str(row["user_host_name"])
                if row["user_host_name"] is not None
                else None
            ),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
