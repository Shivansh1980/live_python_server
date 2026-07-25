class FileServiceError(Exception):
    """Base error for file-service failures."""


class InvalidFilenameError(FileServiceError):
    """Raised when a requested name could escape the download directory."""


class FileNotAvailableError(FileServiceError):
    """Raised when a requested file is not available for download."""


class FileAlreadyExistsError(FileServiceError):
    """Raised when an upload would overwrite an existing file."""


class FileTooLargeError(FileServiceError):
    """Raised when an uploaded file exceeds the configured limit."""


class ContactNotFoundError(Exception):
    """Raised when an admin operation targets an unknown contact."""


class AnalyticsEventNotFoundError(Exception):
    """Raised when an admin operation targets an unknown analytics event."""
