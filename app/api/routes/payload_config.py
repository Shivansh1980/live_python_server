from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_payload_config_service
from app.domain.exceptions import PayloadConfigNotFoundError
from app.schemas.payload_config import (
    PayloadConfigResponse,
    PayloadReplacementUpdateRequest,
    PayloadReplacementUpdateResponse,
)
from app.services.payload_config_service import PayloadConfigService

router = APIRouter(prefix="/payloadconfig", tags=["payload configuration"])


@router.get(
    "/",
    response_model=PayloadConfigResponse,
    summary="Get the newest active payload configuration for an IP address",
)
def get_payload_config(
    user_ip_address: Annotated[str, Query()],
    service: PayloadConfigService = Depends(get_payload_config_service),
) -> PayloadConfigResponse:
    try:
        payload_config = service.get_latest_active_by_ip(user_ip_address)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_ip_address must be a valid IPv4 or IPv6 address.",
        ) from exc
    except PayloadConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return PayloadConfigResponse.model_validate(payload_config)


@router.post(
    "/",
    response_model=PayloadReplacementUpdateResponse,
    summary="Update payload replacement for one user or every row",
)
def update_payload_replacement(
    payload: PayloadReplacementUpdateRequest | None = None,
    service: PayloadConfigService = Depends(get_payload_config_service),
) -> PayloadReplacementUpdateResponse:
    requested = payload or PayloadReplacementUpdateRequest()
    try:
        result = service.set_should_replace(
            requested.should_replace_payload,
            user_ip_address=requested.user_ip_address,
            user_host_name=requested.user_host_name,
        )
    except PayloadConfigNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return PayloadReplacementUpdateResponse.model_validate(result)
