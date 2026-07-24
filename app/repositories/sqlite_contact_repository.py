import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.domain.models import Contact, ContactStatus, NewContact

SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    company TEXT NOT NULL DEFAULT '',
    project_type TEXT NOT NULL DEFAULT '',
    budget TEXT NOT NULL DEFAULT '',
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new'
        CHECK (status IN ('new', 'read', 'archived')),
    notification_status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contacts_created_at
    ON contacts(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contacts_status
    ON contacts(status);
"""


class SQLiteContactRepository:
    """SQLite persistence with one short-lived connection per operation."""

    def __init__(
        self,
        database_path: Path,
        seed_database_path: Path | None = None,
    ) -> None:
        self._database_path = database_path
        self._seed_database_path = seed_database_path
        self._prepare_database()

    def create(self, contact: NewContact) -> Contact:
        created_at = datetime.now(timezone.utc)
        with self._connection() as connection:
            cursor = connection.execute(
                """
                INSERT INTO contacts (
                    name, email, company, project_type, budget, message,
                    status, notification_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    contact.name,
                    contact.email,
                    contact.company,
                    contact.project_type,
                    contact.budget,
                    contact.message,
                    ContactStatus.NEW.value,
                    "queued",
                    created_at.isoformat(),
                ),
            )
            contact_id = int(cursor.lastrowid)
            connection.commit()
        stored = self.get(contact_id)
        if stored is None:
            raise RuntimeError("Stored contact could not be reloaded.")
        return stored

    def list(
        self,
        *,
        search: str = "",
        status: ContactStatus | None = None,
        limit: int = 100,
    ) -> list[Contact]:
        clauses: list[str] = []
        parameters: list[object] = []
        if search:
            clauses.append(
                "(name LIKE ? OR email LIKE ? OR company LIKE ? OR message LIKE ?)"
            )
            term = f"%{search}%"
            parameters.extend([term, term, term, term])
        if status is not None:
            clauses.append("status = ?")
            parameters.append(status.value)

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        parameters.append(max(1, min(limit, 500)))
        with self._connection() as connection:
            rows = connection.execute(
                f"""
                SELECT *
                FROM contacts
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                parameters,
            ).fetchall()
        return [self._to_contact(row) for row in rows]

    def get(self, contact_id: int) -> Contact | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM contacts WHERE id = ?",
                (contact_id,),
            ).fetchone()
        return self._to_contact(row) if row else None

    def count(self, status: ContactStatus | None = None) -> int:
        query = "SELECT COUNT(*) FROM contacts"
        parameters: tuple[object, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            parameters = (status.value,)
        with self._connection() as connection:
            return int(connection.execute(query, parameters).fetchone()[0])

    def update_status(
        self,
        contact_id: int,
        status: ContactStatus,
    ) -> Contact | None:
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE contacts SET status = ? WHERE id = ?",
                (status.value, contact_id),
            )
            connection.commit()
        if cursor.rowcount == 0:
            return None
        return self.get(contact_id)

    def update_notification_status(
        self,
        contact_id: int,
        notification_status: str,
    ) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE contacts SET notification_status = ? WHERE id = ?",
                (notification_status[:1000], contact_id),
            )
            connection.commit()

    def delete(self, contact_id: int) -> bool:
        with self._connection() as connection:
            cursor = connection.execute(
                "DELETE FROM contacts WHERE id = ?",
                (contact_id,),
            )
            connection.commit()
        return cursor.rowcount > 0

    def _prepare_database(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        if (
            not self._database_path.exists()
            and self._seed_database_path is not None
            and self._seed_database_path.exists()
            and self._seed_database_path.resolve() != self._database_path.resolve()
        ):
            shutil.copy2(self._seed_database_path, self._database_path)
        with self._connection() as connection:
            connection.executescript(SCHEMA)
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
    def _to_contact(row: sqlite3.Row) -> Contact:
        return Contact(
            id=int(row["id"]),
            name=str(row["name"]),
            email=str(row["email"]),
            company=str(row["company"]),
            project_type=str(row["project_type"]),
            budget=str(row["budget"]),
            message=str(row["message"]),
            status=ContactStatus(str(row["status"])),
            notification_status=str(row["notification_status"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
