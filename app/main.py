from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.repositories.local_file_repository import LocalFileRepository
from app.services.file_service import FileService


def create_app(settings: Settings | None = None) -> FastAPI:
    """Application factory that keeps construction separate from behavior."""
    resolved_settings = settings or get_settings()
    repository = LocalFileRepository(resolved_settings.download_directory)
    file_service = FileService(repository)

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description=(
            "Lists and downloads files that are stored directly in the "
            "downloadable_files directory."
        ),
    )
    application.state.settings = resolved_settings
    application.state.file_service = file_service
    application.include_router(api_router)
    return application


app = create_app()
