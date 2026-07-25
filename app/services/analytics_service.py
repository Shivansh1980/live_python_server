import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit, urlunsplit

from app.domain.analytics import (
    AnalyticsEvent,
    AnalyticsEventType,
    NewAnalyticsEvent,
)
from app.domain.exceptions import AnalyticsEventNotFoundError
from app.repositories.analytics_contracts import AnalyticsRepository
from app.schemas.analytics import AnalyticsEventRequest


class AnalyticsService:
    def __init__(self, repository: AnalyticsRepository) -> None:
        self._repository = repository

    @property
    def recording_enabled(self) -> bool:
        return self._repository.is_recording_enabled()

    def set_recording_enabled(self, enabled: bool) -> None:
        self._repository.set_recording_enabled(enabled)

    def record(
        self,
        payload: AnalyticsEventRequest,
        user_agent: str,
    ) -> AnalyticsEvent | None:
        if not self.recording_enabled:
            return None
        event = NewAnalyticsEvent(
            session_id=payload.session_id,
            event_type=payload.event_type,
            page_url=self._sanitize_url(payload.page_url),
            page_title=payload.page_title,
            section=payload.section,
            element_tag=payload.element_tag.casefold(),
            element_id=payload.element_id,
            element_label=payload.element_label,
            duration_ms=payload.duration_ms,
            scroll_depth=payload.scroll_depth,
            pointer_x=payload.pointer_x,
            pointer_y=payload.pointer_y,
            viewport_width=payload.viewport_width,
            viewport_height=payload.viewport_height,
            metadata_json=json.dumps(
                payload.metadata,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            ),
            user_agent=user_agent[:500],
            occurred_at=self._normalize_occurred_at(payload.occurred_at),
        )
        return self._repository.create(event)

    def get(self, event_id: int) -> AnalyticsEvent:
        event = self._repository.get(event_id)
        if event is None:
            raise AnalyticsEventNotFoundError(
                f"Analytics event {event_id} was not found."
            )
        return event

    def list(
        self,
        *,
        search: str = "",
        event_type: AnalyticsEventType | None = None,
        limit: int = 200,
    ) -> list[AnalyticsEvent]:
        return self._repository.list(
            search=search.strip(),
            event_type=event_type,
            limit=limit,
        )

    def summary(self) -> dict[str, object]:
        return self._repository.summary()

    def delete(self, event_id: int) -> None:
        if not self._repository.delete(event_id):
            raise AnalyticsEventNotFoundError(
                f"Analytics event {event_id} was not found."
            )

    def delete_all(self) -> int:
        return self._repository.delete_all()

    @staticmethod
    def _sanitize_url(value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"} and parsed.hostname:
            netloc = parsed.hostname
            try:
                port = parsed.port
            except ValueError:
                return (parsed.path or "/")[:500]
            if port is not None:
                netloc = f"{netloc}:{port}"
            return urlunsplit(
                (parsed.scheme, netloc, parsed.path or "/", "", "")
            )[:500]
        return (parsed.path or "/")[:500]

    @staticmethod
    def _normalize_occurred_at(value: datetime | None) -> datetime:
        now = datetime.now(timezone.utc)
        if value is None:
            return now
        normalized = (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )
        if normalized > now + timedelta(minutes=5):
            return now
        if normalized < now - timedelta(days=30):
            return now - timedelta(days=30)
        return normalized
