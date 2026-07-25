from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.dependencies import (
    get_analytics_rate_limiter,
    get_analytics_service,
)
from app.core.request_context import client_identifier
from app.schemas.analytics import AnalyticsEventRequest, AnalyticsEventResponse
from app.services.analytics_service import AnalyticsService
from app.services.rate_limiter import SlidingWindowRateLimiter

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post(
    "/events",
    response_model=AnalyticsEventResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Record an anonymous website interaction",
)
def record_event(
    payload: AnalyticsEventRequest,
    request: Request,
    service: AnalyticsService = Depends(get_analytics_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(
        get_analytics_rate_limiter
    ),
) -> AnalyticsEventResponse:
    if not service.recording_enabled:
        return AnalyticsEventResponse(
            recorded=False,
            event_id=None,
            reason="recording_disabled",
        )
    rate_limit_key = f"{client_identifier(request)}:{payload.session_id}"
    if not rate_limiter.allow(rate_limit_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many analytics events. Please retry later.",
        )
    event = service.record(
        payload,
        request.headers.get("user-agent", ""),
    )
    return AnalyticsEventResponse(
        recorded=event is not None,
        event_id=event.id if event else None,
        reason="recorded" if event else "recording_disabled",
    )
