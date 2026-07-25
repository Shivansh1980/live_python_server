"""Create the versioned, empty SQLite database used for first deployment."""

from pathlib import Path

from app.repositories.sqlite_analytics_repository import (
    SQLiteAnalyticsRepository,
)
from app.repositories.sqlite_contact_repository import SQLiteContactRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED_DATABASE = PROJECT_ROOT / "data" / "app_seed.db"


def main() -> None:
    if SEED_DATABASE.exists():
        SEED_DATABASE.unlink()
    SQLiteContactRepository(SEED_DATABASE, seed_database_path=None)
    SQLiteAnalyticsRepository(SEED_DATABASE)
    print(f"Created empty seed database: {SEED_DATABASE}")


if __name__ == "__main__":
    main()
