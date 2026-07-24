from pathlib import Path
from typing import BinaryIO, Protocol

from app.domain.models import DownloadableFile


class DownloadFileRepository(Protocol):
    """Storage contract consumed by the application service."""

    def list_files(self) -> list[DownloadableFile]:
        ...

    def get_file(self, filename: str) -> Path:
        ...

    def save_file(
        self,
        filename: str,
        source: BinaryIO,
        max_bytes: int,
    ) -> Path:
        ...

    def delete_file(self, filename: str) -> None:
        ...
