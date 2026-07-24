class FileServiceError(Exception):
    """Base error for file-service failures."""


class InvalidFilenameError(FileServiceError):
    """Raised when a requested name could escape the download directory."""


class FileNotAvailableError(FileServiceError):
    """Raised when a requested file is not available for download."""
