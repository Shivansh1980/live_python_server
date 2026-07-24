from datetime import datetime, timezone
from pathlib import Path

from app.domain.exceptions import FileNotAvailableError, InvalidFilenameError
from app.domain.models import DownloadableFile


class LocalFileRepository:
    """Expose only regular, non-symlink files directly inside one fixed directory."""

    def __init__(self, root_directory: Path) -> None:
        root_directory.mkdir(parents=True, exist_ok=True)
        self._root_directory = root_directory.resolve(strict=True)

    def list_files(self) -> list[DownloadableFile]:
        files: list[DownloadableFile] = []
        for candidate in self._root_directory.iterdir():
            if candidate.is_symlink() or not candidate.is_file():
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

    @staticmethod
    def _validate_filename(filename: str) -> None:
        if (
            not filename
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or Path(filename).name != filename
        ):
            raise InvalidFilenameError("Only direct filenames are allowed.")
