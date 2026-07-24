from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    name: str
    size_bytes: int
    modified_at: datetime
    download_url: str


class FileListResponse(BaseModel):
    count: int
    files: list[FileMetadata]
