from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def download_directory(tmp_path: Path) -> Path:
    directory = tmp_path / "downloadable_files"
    directory.mkdir()
    return directory


@pytest.fixture
def client(download_directory: Path) -> Iterator[TestClient]:
    temporary_root = download_directory.parent
    app = create_app(
        Settings(
            download_directory=download_directory,
            database_path=temporary_root / "app.db",
            seed_database_path=None,
            admin_username="test-admin",
            admin_password="unit-test-only-password",
            session_secret="test-session-secret-that-is-long-enough",
            cors_allowed_origins=(
                "http://localhost:3000",
                "http://127.0.0.1:3000",
            ),
        )
    )
    with TestClient(app) as test_client:
        yield test_client
