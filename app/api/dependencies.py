from fastapi import Request

from app.services.auth_service import AdminAuthService
from app.services.contact_service import ContactService
from app.services.file_service import FileService
from app.services.rate_limiter import SlidingWindowRateLimiter


def get_file_service(request: Request) -> FileService:
    """Resolve the file service configured by the application factory."""
    return request.app.state.file_service


def get_contact_service(request: Request) -> ContactService:
    return request.app.state.contact_service


def get_admin_auth_service(request: Request) -> AdminAuthService:
    return request.app.state.admin_auth_service


def get_contact_rate_limiter(request: Request) -> SlidingWindowRateLimiter:
    return request.app.state.contact_rate_limiter
