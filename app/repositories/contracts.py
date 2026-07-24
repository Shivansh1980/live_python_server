from pathlib import Path
from typing import Protocol

from app.domain.models import DownloadableFile


class DownloadFileRepository(Protocol):
    """Storage contract consumed by the application service."""

    def list_files(self) -> list[DownloadableFile]:
        ...

    def get_file(self, filename: str) -> Path:
        ...
