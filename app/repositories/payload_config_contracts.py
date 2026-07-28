from typing import Protocol

from app.domain.payload_config import NewPayloadConfig, PayloadConfig


class PayloadConfigRepository(Protocol):
    def create(self, payload_config: NewPayloadConfig) -> PayloadConfig:
        ...

    def get(self, payload_config_id: int) -> PayloadConfig | None:
        ...

    def get_latest_active_by_ip(
        self,
        user_ip_address: str,
    ) -> PayloadConfig | None:
        ...

    def list(
        self,
        *,
        search: str = "",
        limit: int = 200,
    ) -> list[PayloadConfig]:
        ...

    def update(
        self,
        payload_config_id: int,
        payload_config: NewPayloadConfig,
    ) -> PayloadConfig | None:
        ...

    def update_partial(
        self,
        payload_config_id: int,
        changes: dict[str, object],
    ) -> PayloadConfig | None:
        ...

    def update_should_replace_for_latest_active(
        self,
        user_ip_address: str,
        should_replace_payload: bool,
    ) -> PayloadConfig | None:
        ...

    def update_should_replace_for_latest_active_hostname(
        self,
        user_host_name: str,
        should_replace_payload: bool,
    ) -> PayloadConfig | None:
        ...

    def update_should_replace_for_all(
        self,
        should_replace_payload: bool,
    ) -> int:
        ...

    def delete(self, payload_config_id: int) -> bool:
        ...
