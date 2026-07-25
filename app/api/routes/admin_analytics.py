import json
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.admin_support import flash, require_admin, template, verify_csrf
from app.api.dependencies import (
    get_admin_auth_service,
    get_analytics_service,
)
from app.domain.analytics import AnalyticsEventType
from app.domain.exceptions import AnalyticsEventNotFoundError
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AdminAuthService

router = APIRouter(
    prefix="/admin/analytics",
    tags=["admin"],
    include_in_schema=False,
)


@router.get("", response_class=HTMLResponse)
def analytics_dashboard(
    request: Request,
    q: Annotated[str, Query(max_length=100)] = "",
    event_type_filter: Annotated[str, Query(alias="event_type")] = "",
    analytics: AnalyticsService = Depends(get_analytics_service),
) -> HTMLResponse:
    require_admin(request)
    selected_type = _parse_event_type(event_type_filter)
    return template(
        request,
        "admin/analytics.html",
        {
            "events": analytics.list(
                search=q,
                event_type=selected_type,
                limit=300,
            ),
            "summary": analytics.summary(),
            "recording_enabled": analytics.recording_enabled,
            "query": q,
            "event_type_filter": (
                selected_type.value if selected_type else ""
            ),
            "event_types": tuple(AnalyticsEventType),
            "csrf_token": request.session["csrf_token"],
            "flash": request.session.pop("flash", None),
        },
    )


@router.get("/events/{event_id}", response_class=HTMLResponse)
def analytics_event_detail(
    event_id: int,
    request: Request,
    analytics: AnalyticsService = Depends(get_analytics_service),
) -> HTMLResponse:
    require_admin(request)
    try:
        event = analytics.get(event_id)
    except AnalyticsEventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return template(
        request,
        "admin/analytics_detail.html",
        {
            "event": event,
            "metadata": json.loads(event.metadata_json),
            "csrf_token": request.session["csrf_token"],
            "flash": request.session.pop("flash", None),
        },
    )


@router.post("/settings")
def update_analytics_settings(
    request: Request,
    csrf_token: Annotated[str, Form()],
    enabled: Annotated[str | None, Form()] = None,
    auth: AdminAuthService = Depends(get_admin_auth_service),
    analytics: AnalyticsService = Depends(get_analytics_service),
) -> RedirectResponse:
    require_admin(request)
    verify_csrf(request, csrf_token, auth)
    recording_enabled = enabled == "on"
    analytics.set_recording_enabled(recording_enabled)
    flash(
        request,
        (
            "Website action recording enabled."
            if recording_enabled
            else "Website action recording paused."
        ),
        "success",
    )
    return RedirectResponse(
        "/admin/analytics",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/events/{event_id}/delete")
def delete_analytics_event(
    event_id: int,
    request: Request,
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
    analytics: AnalyticsService = Depends(get_analytics_service),
) -> RedirectResponse:
    require_admin(request)
    verify_csrf(request, csrf_token, auth)
    try:
        analytics.delete(event_id)
    except AnalyticsEventNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    flash(request, "Analytics event deleted.", "success")
    return RedirectResponse(
        "/admin/analytics",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/events/delete-all")
def delete_all_analytics_events(
    request: Request,
    csrf_token: Annotated[str, Form()],
    auth: AdminAuthService = Depends(get_admin_auth_service),
    analytics: AnalyticsService = Depends(get_analytics_service),
) -> RedirectResponse:
    require_admin(request)
    verify_csrf(request, csrf_token, auth)
    deleted_count = analytics.delete_all()
    flash(
        request,
        f"Deleted {deleted_count} analytics events.",
        "success",
    )
    return RedirectResponse(
        "/admin/analytics",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _parse_event_type(value: str) -> AnalyticsEventType | None:
    if not value:
        return None
    try:
        return AnalyticsEventType(value)
    except ValueError:
        return None
