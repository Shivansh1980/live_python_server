from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.repositories.local_file_repository import LocalFileRepository
from app.repositories.sqlite_contact_repository import SQLiteContactRepository
from app.services.auth_service import AdminAuthService
from app.services.contact_service import ContactService
from app.services.file_service import FileService
from app.services.notification_service import (
    DiscordNotifier,
    GmailSmtpNotifier,
    NotificationDispatcher,
)
from app.services.rate_limiter import SlidingWindowRateLimiter


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory that keeps construction separate from behavior."""
    resolved_settings = settings or get_settings()
    _validate_production_settings(resolved_settings)

    file_repository = LocalFileRepository(
        resolved_settings.download_directory
    )
    contact_repository = SQLiteContactRepository(
        resolved_settings.database_path,
        resolved_settings.seed_database_path,
    )
    notifications = _build_notification_dispatcher(resolved_settings)
    file_service = FileService(file_repository)
    contact_service = ContactService(contact_repository, notifications)
    admin_auth_service = AdminAuthService(
        resolved_settings.admin_username,
        resolved_settings.admin_password,
    )

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "Accepts contact enquiries and securely lists and downloads files "
            "stored directly in media/downloadable_files."
        ),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=600,
    )
    application.add_middleware(
        SessionMiddleware,
        secret_key=resolved_settings.session_secret,
        session_cookie="curvature_admin",
        max_age=8 * 60 * 60,
        same_site="lax",
        https_only=resolved_settings.is_production,
    )
    application.mount(
        "/static",
        StaticFiles(directory=resolved_settings.static_directory),
        name="static",
    )
    application.state.settings = resolved_settings
    application.state.file_service = file_service
    application.state.contact_service = contact_service
    application.state.admin_auth_service = admin_auth_service
    application.state.contact_rate_limiter = SlidingWindowRateLimiter(
        max_requests=5,
        window_seconds=10 * 60,
    )
    application.state.admin_rate_limiter = SlidingWindowRateLimiter(
        max_requests=5,
        window_seconds=15 * 60,
    )
    application.state.templates = Jinja2Templates(
        directory=resolved_settings.templates_directory
    )
    application.include_router(api_router)
    return application


def _build_notification_dispatcher(
    settings: Settings,
) -> NotificationDispatcher:
    notifiers = []
    if settings.discord_webhook_url:
        notifiers.append(DiscordNotifier(settings.discord_webhook_url))
    if (
        settings.smtp_username
        and settings.smtp_app_password
        and settings.notification_email_to
    ):
        notifiers.append(
            GmailSmtpNotifier(
                host=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_username,
                app_password=settings.smtp_app_password,
                recipient=settings.notification_email_to,
            )
        )
    return NotificationDispatcher(notifiers)


def _validate_production_settings(settings: Settings) -> None:
    if (
        settings.is_production
        and settings.admin_enabled
        and settings.session_secret == "development-only-session-secret"
    ):
        raise RuntimeError("SESSION_SECRET must be configured in production.")


app = create_app()
