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
    app = create_app(Settings(download_directory=download_directory))
    with TestClient(app) as test_client:
        yield test_client
