import os
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.domain.exceptions import (
    FileAlreadyExistsError,
    FileNotAvailableError,
    FileTooLargeError,
    InvalidFilenameError,
)
from app.domain.models import DownloadableFile


class LocalFileRepository:
    """Expose only regular, non-symlink files directly inside one fixed directory."""

    def __init__(self, root_directory: Path) -> None:
        root_directory.mkdir(parents=True, exist_ok=True)
        self._root_directory = root_directory.resolve(strict=True)

    def list_files(self) -> list[DownloadableFile]:
        files: list[DownloadableFile] = []
        for candidate in self._root_directory.iterdir():
            if (
                candidate.name.startswith(".")
                or candidate.is_symlink()
                or not candidate.is_file()
            ):
                continue
            resolved = candidate.resolve(strict=True)
            if resolved.parent != self._root_directory:
                continue
            stat = resolved.stat()
            files.append(
                DownloadableFile(
                    name=candidate.name,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(
                        stat.st_mtime,
                        tz=timezone.utc,
                    ),
                )
            )
        return sorted(files, key=lambda item: item.name.casefold())

    def get_file(self, filename: str) -> Path:
        self._validate_filename(filename)
        candidate = self._root_directory / filename

        if candidate.is_symlink() or not candidate.is_file():
            raise FileNotAvailableError(f"File '{filename}' was not found.")

        resolved = candidate.resolve(strict=True)
        if resolved.parent != self._root_directory:
            raise InvalidFilenameError("Only direct filenames are allowed.")
        return resolved

    def save_file(
        self,
        filename: str,
        source: BinaryIO,
        max_bytes: int,
    ) -> Path:
        self._validate_filename(filename)
        destination = self._root_directory / filename
        if destination.exists() or destination.is_symlink():
            raise FileAlreadyExistsError(f"File '{filename}' already exists.")

        temporary = self._root_directory / f".{uuid4().hex}.uploading"
        bytes_written = 0
        try:
            with temporary.open("xb") as output:
                while chunk := source.read(1024 * 1024):
                    bytes_written += len(chunk)
                    if bytes_written > max_bytes:
                        raise FileTooLargeError(
                            f"File exceeds the {max_bytes} byte upload limit."
                        )
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError as exc:
                raise FileAlreadyExistsError(
                    f"File '{filename}' already exists."
                ) from exc
            temporary.unlink()
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return destination.resolve(strict=True)

    def delete_file(self, filename: str) -> None:
        file_path = self.get_file(filename)
        file_path.unlink()

    @staticmethod
    def _validate_filename(filename: str) -> None:
        if (
            not filename
            or filename in {".", ".."}
            or filename.startswith(".")
            or "/" in filename
            or "\\" in filename
            or Path(filename).name != filename
        ):
            raise InvalidFilenameError("Only direct filenames are allowed.")
