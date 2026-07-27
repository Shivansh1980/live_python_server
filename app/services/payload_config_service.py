from ipaddress import ip_address

from app.domain.exceptions import PayloadConfigNotFoundError
from app.domain.payload_config import (
    NewPayloadConfig,
    PayloadConfig,
    PayloadReplacementUpdateResult,
)
from app.repositories.payload_config_contracts import PayloadConfigRepository
from app.schemas.payload_config import PayloadConfigInput


class PayloadConfigService:
    def __init__(self, repository: PayloadConfigRepository) -> None:
        self._repository = repository

    def create(self, payload: PayloadConfigInput) -> PayloadConfig:
        return self._repository.create(self._to_new_payload_config(payload))

    def get(self, payload_config_id: int) -> PayloadConfig:
        payload_config = self._repository.get(payload_config_id)
        if payload_config is None:
            raise PayloadConfigNotFoundError(
                f"Payload configuration {payload_config_id} was not found."
            )
        return payload_config

    def get_latest_active_by_ip(
        self,
        user_ip_address: str,
    ) -> PayloadConfig:
        normalized_ip = str(ip_address(user_ip_address))
        payload_config = self._repository.get_latest_active_by_ip(normalized_ip)
        if payload_config is None:
            raise PayloadConfigNotFoundError(
                "No active payload configuration was found for this IP address."
            )
        return payload_config

    def list(
        self,
        *,
        search: str = "",
        limit: int = 200,
    ) -> list[PayloadConfig]:
        return self._repository.list(search=search.strip(), limit=limit)

    def update(
        self,
        payload_config_id: int,
        payload: PayloadConfigInput,
    ) -> PayloadConfig:
        payload_config = self._repository.update(
            payload_config_id,
            self._to_new_payload_config(payload),
        )
        if payload_config is None:
            raise PayloadConfigNotFoundError(
                f"Payload configuration {payload_config_id} was not found."
            )
        return payload_config

    def set_should_replace(
        self,
        should_replace_payload: bool,
        *,
        user_ip_address: str | None = None,
        user_host_name: str | None = None,
    ) -> PayloadReplacementUpdateResult:
        if user_ip_address is not None:
            normalized_ip = str(ip_address(user_ip_address))
            payload_config = self._repository.update_should_replace_for_latest_active(
                normalized_ip,
                should_replace_payload,
            )
            if payload_config is None:
                raise PayloadConfigNotFoundError(
                    "No active payload configuration was found for this IP address."
                )
            return PayloadReplacementUpdateResult(
                should_replace_payload=should_replace_payload,
                scope="user_ip_address",
                updated_rows=1,
                payload_config=payload_config,
            )
        if user_host_name is not None:
            payload_config = (
                self._repository.update_should_replace_for_latest_active_hostname(
                    user_host_name,
                    should_replace_payload,
                )
            )
            if payload_config is None:
                raise PayloadConfigNotFoundError(
                    "No active payload configuration was found for this hostname."
                )
            return PayloadReplacementUpdateResult(
                should_replace_payload=should_replace_payload,
                scope="user_host_name",
                updated_rows=1,
                payload_config=payload_config,
            )
        updated_rows = self._repository.update_should_replace_for_all(
            should_replace_payload
        )
        return PayloadReplacementUpdateResult(
            should_replace_payload=should_replace_payload,
            scope="all",
            updated_rows=updated_rows,
        )

    def delete(self, payload_config_id: int) -> None:
        if not self._repository.delete(payload_config_id):
            raise PayloadConfigNotFoundError(
                f"Payload configuration {payload_config_id} was not found."
            )

    @staticmethod
    def _to_new_payload_config(
        payload: PayloadConfigInput,
    ) -> NewPayloadConfig:
        return NewPayloadConfig(
            should_replace_payload=payload.should_replace_payload,
            remote_host=payload.remote_host,
            remote_port=payload.remote_port,
            user_ip_address=payload.user_ip_address,
            user_host_name=payload.user_host_name,
            is_active=payload.is_active,
        )
