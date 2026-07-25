from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.analytics import AnalyticsEventType

MetadataValue = str | int | float | bool | None


class AnalyticsEventRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    session_id: Annotated[
        str,
        Field(
            min_length=8,
            max_length=100,
            pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
        ),
    ]
    event_type: AnalyticsEventType
    page_url: Annotated[str, Field(min_length=1, max_length=2048)]
    page_title: Annotated[str, Field(max_length=200)] = ""
    section: Annotated[str, Field(max_length=120)] = ""
    element_tag: Annotated[str, Field(max_length=30)] = ""
    element_id: Annotated[str, Field(max_length=120)] = ""
    element_label: Annotated[str, Field(max_length=160)] = ""
    duration_ms: Annotated[int | None, Field(ge=0, le=3_600_000)] = None
    scroll_depth: Annotated[float | None, Field(ge=0, le=100)] = None
    pointer_x: Annotated[float | None, Field(ge=0, le=100)] = None
    pointer_y: Annotated[float | None, Field(ge=0, le=100)] = None
    viewport_width: Annotated[int | None, Field(ge=200, le=20_000)] = None
    viewport_height: Annotated[int | None, Field(ge=200, le=20_000)] = None
    occurred_at: datetime | None = None
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_frontend_field_names(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        aliases = {
            "sessionId": "session_id",
            "eventType": "event_type",
            "pageUrl": "page_url",
            "pageTitle": "page_title",
            "elementTag": "element_tag",
            "elementId": "element_id",
            "elementLabel": "element_label",
            "durationMs": "duration_ms",
            "scrollDepth": "scroll_depth",
            "pointerX": "pointer_x",
            "pointerY": "pointer_y",
            "viewportWidth": "viewport_width",
            "viewportHeight": "viewport_height",
            "occurredAt": "occurred_at",
        }
        normalized = dict(value)
        for frontend_name, internal_name in aliases.items():
            if frontend_name in normalized and internal_name not in normalized:
                normalized[internal_name] = normalized.pop(frontend_name)
        return normalized

    @field_validator("metadata")
    @classmethod
    def validate_metadata(
        cls,
        metadata: dict[str, MetadataValue],
    ) -> dict[str, MetadataValue]:
        if len(metadata) > 20:
            raise ValueError("metadata supports at most 20 fields")
        sensitive_terms = (
            "password",
            "passcode",
            "token",
            "secret",
            "cookie",
            "authorization",
            "email",
            "phone",
            "message",
            "credit",
            "card",
            "inputvalue",
            "input_value",
        )
        for key, item in metadata.items():
            normalized_key = key.casefold().replace("-", "_")
            if len(key) > 60:
                raise ValueError("metadata keys must not exceed 60 characters")
            if any(term in normalized_key for term in sensitive_terms):
                raise ValueError(f"Sensitive metadata key is not allowed: {key}")
            if isinstance(item, str) and len(item) > 300:
                raise ValueError(
                    "metadata string values must not exceed 300 characters"
                )
        return metadata


class AnalyticsEventResponse(BaseModel):
    recorded: bool
    event_id: int | None
    reason: str
