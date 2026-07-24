from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DownloadableFile:
    name: str
    size_bytes: int
    modified_at: datetime
