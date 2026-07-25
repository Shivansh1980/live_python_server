from typing import Protocol

from app.domain.analytics import (
    AnalyticsEvent,
    AnalyticsEventType,
    NewAnalyticsEvent,
)


class AnalyticsRepository(Protocol):
    def is_recording_enabled(self) -> bool:
        ...

    def set_recording_enabled(self, enabled: bool) -> None:
        ...

    def create(self, event: NewAnalyticsEvent) -> AnalyticsEvent | None:
        ...

    def get(self, event_id: int) -> AnalyticsEvent | None:
        ...

    def list(
        self,
        *,
        search: str = "",
        event_type: AnalyticsEventType | None = None,
        limit: int = 200,
    ) -> list[AnalyticsEvent]:
        ...

    def summary(self) -> dict[str, object]:
        ...

    def delete(self, event_id: int) -> bool:
        ...

    def delete_all(self) -> int:
        ...
