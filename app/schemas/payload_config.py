from datetime import datetime
from ipaddress import ip_address
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class PayloadConfigInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    should_replace_payload: bool = False
    remote_host: Annotated[str | None, Field(max_length=253)] = None
    remote_port: Annotated[int | None, Field(ge=1, le=65535)] = None
    user_ip_address: Annotated[str | None, Field(max_length=45)] = None
    user_host_name: Annotated[str | None, Field(max_length=253)] = None
    is_active: bool = True

    @field_validator(
        "remote_host",
        "user_ip_address",
        "user_host_name",
        mode="before",
    )
    @classmethod
    def empty_strings_are_absent(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("user_ip_address")
    @classmethod
    def normalize_ip_address(cls, value: str | None) -> str | None:
        return str(ip_address(value)) if value is not None else None


class PayloadConfigPatchRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    should_replace_payload: bool | None = None
    remote_host: Annotated[str | None, Field(max_length=253)] = None
    remote_port: Annotated[int | None, Field(ge=1, le=65535)] = None
    user_ip_address: Annotated[str | None, Field(max_length=45)] = None
    user_host_name: Annotated[str | None, Field(max_length=253)] = None
    is_active: bool | None = None

    @field_validator(
        "remote_host",
        "user_ip_address",
        "user_host_name",
        mode="before",
    )
    @classmethod
    def empty_strings_are_absent(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("user_ip_address")
    @classmethod
    def normalize_ip_address(cls, value: str | None) -> str | None:
        return str(ip_address(value)) if value is not None else None

    @model_validator(mode="after")
    def require_valid_change(self) -> "PayloadConfigPatchRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be supplied.")
        for field_name in ("should_replace_payload", "is_active"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null.")
        return self


class PayloadConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    should_replace_payload: bool
    remote_host: str | None
    remote_port: int | None
    user_ip_address: str | None
    user_host_name: str | None
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
