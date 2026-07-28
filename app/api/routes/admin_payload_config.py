from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError

from app.api.admin_support import flash, require_admin, template, verify_csrf
from app.api.dependencies import (
    get_admin_auth_service,
    get_payload_config_service,
)
from app.domain.exceptions import PayloadConfigNotFoundError
from app.schemas.payload_config import PayloadConfigInput
from app.services.auth_service import AdminAuthService
from app.services.payload_config_service import PayloadConfigService

router = APIRouter(
    prefix="/admin/payload-configs",
    tags=["admin"],
    include_in_schema=False,
)


@router.get("", response_class=HTMLResponse)
def payload_config_list(
    request: Request,
    q: Annotated[str, Query(max_length=100)] = "",
    service: PayloadConfigService = Depends(get_payload_config_service),
) -> HTMLResponse:
    require_admin(request)
    return template(
        request,
        "admin/payload_configs.html",
        {
            "payload_configs": service.list(search=q, limit=300),
            "query": q,
            "csrf_token": request.session["csrf_token"],
            "flash": request.session.pop("flash", None),
        },
    )


@router.post("")
def create_payload_config(
    request: Request,
    csrf_token: Annotated[str, Form()],
    remote_host: Annotated[str | None, Form()] = None,
    remote_port: Annotated[str | None, Form()] = None,
    user_ip_address: Annotated[str | None, Form()] = None,
    user_host_name: Annotated[str | None, Form()] = None,
    should_replace_payload: Annotated[str | None, Form()] = None,
    is_active: Annotated[str | None, Form()] = None,
    auth: AdminAuthService = Depends(get_admin_auth_service),
    service: PayloadConfigService = Depends(get_payload_config_service),
) -> RedirectResponse:
    require_admin(request)
    verify_csrf(request, csrf_token, auth)
    try:
        payload = _validate_form(
            should_replace_payload=should_replace_payload,
            remote_host=remote_host,
            remote_port=remote_port,
            user_ip_address=user_ip_address,
            user_host_name=user_host_name,
            is_active=is_active,
        )
        created = service.create(payload)
    except ValidationError as exc:
        flash(request, _validation_message(exc), "error")
        return RedirectResponse(
            "/admin/payload-configs",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    flash(request, f"Payload configuration #{created.id} created.", "success")
    return RedirectResponse(
        f"/admin/payload-configs/{created.id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{payload_config_id}", response_class=HTMLResponse)
def payload_config_detail(
    payload_config_id: int,
    request: Request,
    service: PayloadConfigService = Depends(get_payload_config_service),
) -> HTMLResponse:
    require_admin(request)
    try:
        payload_config = service.get(payload_config_id)
    except PayloadConfigNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return template(
        request,
        "admin/payload_config_detail.html",
        {
            "payload_config": payload_config,
            "csrf_token": request.session["csrf_token"],
            "flash": request.session.pop("flash", None),
        },
    )


@router.post("/{payload_config_id}")
def update_payload_config(
    payload_config_id: int,
    request: Request,
    csrf_token: Annotated[str, Form()],
    remote_host: Annotated[str | None, Form()] = None,
    remote_port: Annotated[str | None, Form()] = None,
    user_ip_address: Annotated[str | None, Form()] = None,
    user_host_name: Annotated[str | None, Form()] = None,
    should_replace_payload: Annotated[str | None, Form()] = None,
    is_active: Annotated[str | None, Form()] = None,
    auth: AdminAuthService = Depends(get_admin_auth_service),
    service: PayloadConfigService = Depends(get_payload_config_service),
) -> RedirectResponse:
    require_admin(request)
    verify_csrf(request, csrf_token, auth)
    try:
        payload = _validate_form(
            should_replace_payload=should_replace_payload,
            remote_host=remote_host,
            remote_port=remote_port,
            user_ip_address=user_ip_address,
            user_host_name=user_host_name,
            is_active=is_active,
        )
        service.update(payload_config_id, payload)
    except ValidationError as exc:
        flash(request, _validation_message(exc), "error")
    except PayloadConfigNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    else:
        flash(request, "Payload configuration updated.", "success")
    return RedirectResponse(
        f"/admin/payload-configs/{payload_config_id}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{payload_config_id}/delete")
def delete_payload_config(
    payload_config_id: int,
    request: Request,
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
    service: PayloadConfigService = Depends(get_payload_config_service),
) -> RedirectResponse:
    require_admin(request)
    verify_csrf(request, csrf_token, auth)
    try:
        service.delete(payload_config_id)
    except PayloadConfigNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    flash(request, "Payload configuration deleted.", "success")
    return RedirectResponse(
        "/admin/payload-configs",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _validate_form(
    *,
    should_replace_payload: str | None,
    remote_host: str | None,
    remote_port: str | None,
    user_ip_address: str | None,
    user_host_name: str | None,
    is_active: str | None,
) -> PayloadConfigInput:
    return PayloadConfigInput.model_validate(
        {
            "should_replace_payload": should_replace_payload == "on",
            "remote_host": remote_host,
            "remote_port": remote_port or None,
            "user_ip_address": user_ip_address,
            "user_host_name": user_host_name,
            "is_active": is_active == "on",
        }
    )


def _validation_message(error: ValidationError) -> str:
    first_error = error.errors()[0]
    field = str(first_error["loc"][-1]).replace("_", " ")
    return f"{field.title()}: {first_error['msg']}"
