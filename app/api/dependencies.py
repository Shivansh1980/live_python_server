from fastapi import Request

from app.services.file_service import FileService


def get_file_service(request: Request) -> FileService:
    """Resolve the file service configured by the application factory."""
    return request.app.state.file_service
