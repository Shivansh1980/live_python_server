import json

from app.domain.exceptions import ContactNotFoundError
from app.domain.models import Contact, ContactStatus, NewContact
from app.repositories.contact_contracts import ContactRepository
from app.services.notification_service import NotificationDispatcher


class ContactService:
    def __init__(
        self,
        repository: ContactRepository,
        notifications: NotificationDispatcher,
    ) -> None:
        self._repository = repository
        self._notifications = notifications

    @property
    def configured_notification_channels(self) -> tuple[str, ...]:
        return self._notifications.channels

    def submit(self, contact: NewContact) -> Contact:
        return self._repository.create(contact)

    def deliver_notifications(self, contact_id: int) -> None:
        contact = self.get(contact_id)
        outcomes = self._notifications.dispatch(contact)
        self._repository.update_notification_status(
            contact_id,
            json.dumps(outcomes, sort_keys=True),
        )

    def list(
        self,
        *,
        search: str = "",
        status: ContactStatus | None = None,
        limit: int = 100,
    ) -> list[Contact]:
        return self._repository.list(
            search=search.strip(),
            status=status,
            limit=limit,
        )

    def get(self, contact_id: int) -> Contact:
        contact = self._repository.get(contact_id)
        if contact is None:
            raise ContactNotFoundError(
                f"Contact submission {contact_id} was not found."
            )
        return contact

    def counts(self) -> dict[str, int]:
        return {
            "all": self._repository.count(),
            ContactStatus.NEW.value: self._repository.count(ContactStatus.NEW),
            ContactStatus.READ.value: self._repository.count(ContactStatus.READ),
            ContactStatus.ARCHIVED.value: self._repository.count(
                ContactStatus.ARCHIVED
            ),
        }

    def update_status(
        self,
        contact_id: int,
        status: ContactStatus,
    ) -> Contact:
        contact = self._repository.update_status(contact_id, status)
        if contact is None:
            raise ContactNotFoundError(
                f"Contact submission {contact_id} was not found."
            )
        return contact

    def delete(self, contact_id: int) -> None:
        if not self._repository.delete(contact_id):
            raise ContactNotFoundError(
                f"Contact submission {contact_id} was not found."
            )
