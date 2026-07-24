from dataclasses import dataclass
from datetime import datetime
from enum import Enum


@dataclass(frozen=True, slots=True)
class DownloadableFile:
    name: str
    size_bytes: int
    modified_at: datetime


class ContactStatus(str, Enum):
    NEW = "new"
    READ = "read"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class NewContact:
    name: str
    email: str
    company: str
    project_type: str
    budget: str
    message: str


@dataclass(frozen=True, slots=True)
class Contact:
    id: int
    name: str
    email: str
    company: str
    project_type: str
    budget: str
    message: str
    status: ContactStatus
    notification_status: str
    created_at: datetime
