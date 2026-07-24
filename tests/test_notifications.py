from datetime import datetime, timezone

from app.domain.models import Contact, ContactStatus
from app.services.notification_service import NotificationDispatcher


class RecordingNotifier:
    def __init__(self, channel: str, should_fail: bool = False) -> None:
        self._channel = channel
        self._should_fail = should_fail
        self.sent_ids: list[int] = []

    @property
    def channel(self) -> str:
        return self._channel

    def send(self, contact: Contact) -> None:
        if self._should_fail:
            raise RuntimeError("simulated failure")
        self.sent_ids.append(contact.id)


def _contact() -> Contact:
    return Contact(
        id=7,
        name="Jane",
        email="jane@example.com",
        company="Example",
        project_type="Web app",
        budget="$8k–$20k",
        message="A sufficiently detailed project message.",
        status=ContactStatus.NEW,
        notification_status="queued",
        created_at=datetime.now(timezone.utc),
    )


def test_notification_channels_are_failure_isolated() -> None:
    discord = RecordingNotifier("discord")
    email = RecordingNotifier("email", should_fail=True)
    dispatcher = NotificationDispatcher([discord, email])

    outcomes = dispatcher.dispatch(_contact())

    assert outcomes == {"discord": "sent", "email": "failed"}
    assert discord.sent_ids == [7]
