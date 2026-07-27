from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PayloadConfigInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    should_replace_payload: bool = False
    url: Annotated[str, Field(min_length=1, max_length=2048)]
    remote_host: Annotated[str, Field(min_length=1, max_length=253)]
    remote_port: Annotated[int, Field(ge=1, le=65535)]
    user_ip_address: Annotated[str, Field(max_length=45)]
    user_host_name: Annotated[
        str,
        Field(min_length=1, max_length=253),
    ]
    is_active: bool = True

    @field_validator("user_ip_address")
    @classmethod
    def normalize_ip_address(cls, value: str) -> str:
        return str(ip_address(value))


class PayloadConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    should_replace_payload: bool
    url: str
    remote_host: str
    remote_port: int
    user_ip_address: str
    user_host_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PayloadReplacementUpdateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    user_ip_address: Annotated[str | None, Field(max_length=45)] = None
    user_host_name: Annotated[str | None, Field(max_length=253)] = None
    should_replace_payload: bool = False

    @field_validator("user_ip_address", "user_host_name", mode="before")
    @classmethod
    def empty_identifiers_are_absent(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("user_ip_address")
    @classmethod
    def normalize_ip_address(cls, value: str | None) -> str | None:
        return str(ip_address(value)) if value is not None else None


class PayloadReplacementUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    should_replace_payload: bool
    scope: Literal["user_ip_address", "user_host_name", "all"]
    updated_rows: int
    payload_config: PayloadConfigResponse | None = None
