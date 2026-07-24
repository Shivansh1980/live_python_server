from pathlib import Path

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
