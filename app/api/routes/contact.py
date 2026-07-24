from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)

from app.api.dependencies import (
    get_contact_rate_limiter,
    get_contact_service,
)
from app.core.request_context import client_identifier
from app.domain.models import NewContact
from app.schemas.contact import (
    ContactSubmissionRequest,
    ContactSubmissionResponse,
)
from app.services.contact_service import ContactService
from app.services.rate_limiter import SlidingWindowRateLimiter

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post(
    "",
    response_model=ContactSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a contact enquiry",
)
def submit_contact(
    payload: ContactSubmissionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    service: ContactService = Depends(get_contact_service),
    rate_limiter: SlidingWindowRateLimiter = Depends(
        get_contact_rate_limiter
    ),
) -> ContactSubmissionResponse:
    client_key = client_identifier(request)
    if not rate_limiter.allow(client_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many contact requests. Please try again later.",
        )

    if payload.website:
        return ContactSubmissionResponse(
            id=0,
            status="accepted",
            message="Your message has been received.",
        )

    contact = service.submit(
        NewContact(
            name=payload.name,
            email=str(payload.email),
            company=payload.company,
            project_type=payload.project_type,
            budget=payload.budget,
            message=payload.message,
        )
    )
    background_tasks.add_task(service.deliver_notifications, contact.id)
    return ContactSubmissionResponse(
        id=contact.id,
        status="received",
        message="Thank you. Your enquiry has been received.",
    )
