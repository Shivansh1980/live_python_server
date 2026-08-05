import json
import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol
from urllib.request import Request, urlopen

from app.domain.models import Contact
from app.services.contact_email_renderer import ContactEmailRenderer

logger = logging.getLogger(__name__)


class ContactNotifier(Protocol):
    @property
    def channel(self) -> str:
        ...

    def send(self, contact: Contact) -> None:
        ...


class DiscordNotifier:
    def __init__(self, webhook_url: str, timeout_seconds: float = 8) -> None:
        self._webhook_url = webhook_url
        self._timeout_seconds = timeout_seconds

    @property
    def channel(self) -> str:
        return "discord"

    def send(self, contact: Contact) -> None:
        payload = {
            "username": "CurvatureTech Leads",
            "allowed_mentions": {"parse": []},
            "embeds": [
                {
                    "title": f"New enquiry from {contact.name}"[:256],
                    "color": 0x6D5EF7,
                    "fields": [
                        {
                            "name": "Email",
                            "value": contact.email[:1024],
                            "inline": True,
                        },
                        {
                            "name": "Company",
                            "value": (contact.company or "Not provided")[:1024],
                            "inline": True,
                        },
                        {
                            "name": "Project type",
                            "value": (contact.project_type or "Not provided")[
                                :1024
                            ],
                            "inline": True,
                        },
                        {
                            "name": "Budget",
                            "value": (contact.budget or "Not provided")[:1024],
                            "inline": True,
                        },
                        {
                            "name": "Message",
                            "value": contact.message[:1024],
                            "inline": False,
                        },
                    ],
                    "footer": {"text": f"Lead #{contact.id}"},
                    "timestamp": contact.created_at.isoformat(),
                }
            ],
        }
        request = Request(
            self._webhook_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "User-Agent": "CurvatureTech-Contact-API/1.0",
            },
            method="POST",
        )
        with urlopen(request, timeout=self._timeout_seconds) as response:
            if response.status not in {200, 204}:
                raise RuntimeError(
                    f"Discord webhook returned HTTP {response.status}."
                )


class GmailSmtpNotifier:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        app_password: str,
        recipient: str,
        timeout_seconds: float = 10,
        renderer: ContactEmailRenderer | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._app_password = app_password
        self._recipient = recipient
        self._timeout_seconds = timeout_seconds
        self._renderer = renderer or ContactEmailRenderer()

    @property
    def channel(self) -> str:
        return "email"

    def send(self, contact: Contact) -> None:
        rendered = self._renderer.render(contact)
        message = EmailMessage()
        message["Subject"] = rendered.subject
        message["From"] = self._username
        message["To"] = self._recipient
        message["Reply-To"] = contact.email
        message.set_content(rendered.plain_text)
        message.add_alternative(rendered.html, subtype="html")

        with smtplib.SMTP(
            self._host,
            self._port,
            timeout=self._timeout_seconds,
        ) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(self._username, self._app_password)
            smtp.send_message(message)


class NotificationDispatcher:
    def __init__(self, notifiers: list[ContactNotifier] | None = None) -> None:
        self._notifiers = tuple(notifiers or [])

    @property
    def channels(self) -> tuple[str, ...]:
        return tuple(notifier.channel for notifier in self._notifiers)

    def dispatch(self, contact: Contact) -> dict[str, str]:
        if not self._notifiers:
            return {"notifications": "not_configured"}

        outcomes: dict[str, str] = {}
        for notifier in self._notifiers:
            try:
                notifier.send(contact)
                outcomes[notifier.channel] = "sent"
            except Exception:
                logger.exception(
                    "Failed to deliver contact %s through %s.",
                    contact.id,
                    notifier.channel,
                )
                outcomes[notifier.channel] = "failed"
        return outcomes
