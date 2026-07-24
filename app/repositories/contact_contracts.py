from typing import Protocol

from app.domain.models import Contact, ContactStatus, NewContact


class ContactRepository(Protocol):
    def create(self, contact: NewContact) -> Contact:
        ...

    def list(
        self,
        *,
        search: str = "",
        status: ContactStatus | None = None,
        limit: int = 100,
    ) -> list[Contact]:
        ...

    def get(self, contact_id: int) -> Contact | None:
        ...

    def count(self, status: ContactStatus | None = None) -> int:
        ...

    def update_status(
        self,
        contact_id: int,
        status: ContactStatus,
    ) -> Contact | None:
        ...

    def update_notification_status(
        self,
        contact_id: int,
        notification_status: str,
    ) -> None:
        ...

    def delete(self, contact_id: int) -> bool:
        ...
