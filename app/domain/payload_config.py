from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class NewPayloadConfig:
    should_replace_payload: bool
    remote_host: str | None
    remote_port: int | None
    user_ip_address: str | None
    user_host_name: str | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class PayloadConfig:
    id: int
    should_replace_payload: bool
    remote_host: str | None
    remote_port: int | None
    user_ip_address: str | None
    user_host_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class PayloadReplacementUpdateResult:
    should_replace_payload: bool
    scope: str
    updated_rows: int
    payload_config: PayloadConfig | None = None
