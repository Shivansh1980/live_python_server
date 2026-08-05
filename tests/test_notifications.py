from datetime import datetime, timezone
from email.message import EmailMessage

from app.domain.models import Contact, ContactStatus
from app.services.contact_email_renderer import ContactEmailRenderer
from app.services.notification_service import (
    GmailSmtpNotifier,
    NotificationDispatcher,
)


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


def test_contact_email_has_branded_html_and_plain_text_fallback() -> None:
    contact = Contact(
        id=21,
        name="Jane & Partners",
        email="jane@example.com",
        company="<script>alert('unsafe')</script>",
        project_type="Web platform",
        budget="USD 8k-20k",
        message="Hello <b>team</b>.\nPlease contact me soon.",
        status=ContactStatus.NEW,
        notification_status="queued",
        created_at=datetime(2026, 8, 5, 8, 30, tzinfo=timezone.utc),
    )

    rendered = ContactEmailRenderer().render(contact)

    assert rendered.subject == (
        "New project enquiry from Jane & Partners · BuildMind Labs"
    )
    assert "BUILDMIND LABS — NEW PROJECT ENQUIRY" in rendered.plain_text
    assert "Company: <script>alert('unsafe')</script>" in rendered.plain_text
    assert "Reply directly to this email" in rendered.plain_text
    assert "linear-gradient" in rendered.html
    assert "BuildMind Labs leads" in rendered.html
    assert "border:1px solid #dfe3ec" in rendered.html
    assert "box-shadow:0 18px 48px rgba(25,35,61,.20)" in rendered.html
    assert "Reply to Jane &amp; Partners" in rendered.html
    assert "&lt;script&gt;alert(&#x27;unsafe&#x27;)&lt;/script&gt;" in rendered.html
    assert "Hello &lt;b&gt;team&lt;/b&gt;.<br>Please contact me soon." in rendered.html
    assert "<script>alert('unsafe')</script>" not in rendered.html


def test_gmail_notifier_sends_multipart_email_to_new_recipient(
    monkeypatch,
) -> None:
    events: list[object] = []
    sent_messages: list[EmailMessage] = []

    class FakeSmtp:
        def __init__(self, host: str, port: int, timeout: float) -> None:
            events.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback) -> None:
            events.append("close")

        def ehlo(self) -> None:
            events.append("ehlo")

        def starttls(self) -> None:
            events.append("starttls")

        def login(self, username: str, password: str) -> None:
            events.append(("login", username, password))

        def send_message(self, message: EmailMessage) -> None:
            events.append("send_message")
            sent_messages.append(message)

    monkeypatch.setattr(
        "app.services.notification_service.smtplib.SMTP",
        FakeSmtp,
    )
    notifier = GmailSmtpNotifier(
        host="smtp.gmail.com",
        port=587,
        username="sender@gmail.com",
        app_password="unit-test-app-password",
        recipient="shivanshshrivastava2000@gmail.com",
    )

    notifier.send(_contact())

    assert events == [
        ("connect", "smtp.gmail.com", 587, 10),
        "ehlo",
        "starttls",
        "ehlo",
        ("login", "sender@gmail.com", "unit-test-app-password"),
        "send_message",
        "close",
    ]
    assert len(sent_messages) == 1
    message = sent_messages[0]
    assert message["To"] == "shivanshshrivastava2000@gmail.com"
    assert message["From"] == "BuildMind Labs <sender@gmail.com>"
    assert message["Reply-To"] == "jane@example.com"
    assert message.get_content_type() == "multipart/alternative"
    plain_part, html_part = message.iter_parts()
    assert plain_part.get_content_type() == "text/plain"
    assert "A sufficiently detailed project message." in plain_part.get_content()
    assert html_part.get_content_type() == "text/html"
    assert "A new project enquiry arrived" in html_part.get_content()
