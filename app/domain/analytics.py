from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class AnalyticsEventType(str, Enum):
    PAGE_VIEW = "page_view"
    NAVIGATION = "navigation"
    CLICK = "click"
    FOCUS = "focus"
    BLUR = "blur"
    SCROLL = "scroll"
    SECTION_VIEW = "section_view"
    ENGAGEMENT = "engagement"


@dataclass(frozen=True, slots=True)
class NewAnalyticsEvent:
    session_id: str
    event_type: AnalyticsEventType
    page_url: str
    page_title: str
    section: str
    element_tag: str
    element_id: str
    element_label: str
    duration_ms: int | None
    scroll_depth: float | None
    pointer_x: float | None
    pointer_y: float | None
    viewport_width: int | None
    viewport_height: int | None
    metadata_json: str
    user_agent: str
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class AnalyticsEvent:
    id: int
    session_id: str
    event_type: AnalyticsEventType
    page_url: str
    page_title: str
    section: str
    element_tag: str
    element_id: str
    element_label: str
    duration_ms: int | None
    scroll_depth: float | None
    pointer_x: float | None
    pointer_y: float | None
    viewport_width: int | None
    viewport_height: int | None
    metadata_json: str
    user_agent: str
    occurred_at: datetime
    created_at: datetime
