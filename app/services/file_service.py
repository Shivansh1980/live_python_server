from pathlib import Path
from typing import BinaryIO

from app.domain.models import DownloadableFile
from app.repositories.contracts import DownloadFileRepository


class FileService:
    """Use-case layer independent of the underlying file storage."""

    def __init__(self, repository: DownloadFileRepository) -> None:
        self._repository = repository

    def list_files(self) -> list[DownloadableFile]:
        return self._repository.list_files()

    def get_file(self, filename: str) -> Path:
        return self._repository.get_file(filename)

    def save_file(
        self,
        filename: str,
        source: BinaryIO,
        max_bytes: int,
    ) -> Path:
        return self._repository.save_file(filename, source, max_bytes)

    def delete_file(self, filename: str) -> None:
        self._repository.delete_file(filename)
