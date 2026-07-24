from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse

from app.api.dependencies import get_file_service
from app.domain.exceptions import FileNotAvailableError, InvalidFilenameError
from app.schemas.files import FileListResponse, FileMetadata
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["files"])


@router.get("", response_model=FileListResponse, summary="List downloadable files")
def list_files(
    request: Request,
    service: FileService = Depends(get_file_service),
) -> FileListResponse:
    files = [
        FileMetadata(
            name=file.name,
            size_bytes=file.size_bytes,
            modified_at=file.modified_at,
            download_url=str(request.base_url).rstrip("/")
            + "/api/v1/files/"
            + quote(file.name, safe=""),
        )
        for file in service.list_files()
    ]
    return FileListResponse(count=len(files), files=files)


@router.get(
    "/{filename}",
    response_class=FileResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid filename"},
        status.HTTP_404_NOT_FOUND: {"description": "File not found"},
    },
    summary="Download a file by its exact filename",
)
def download_file(
    filename: str,
    service: FileService = Depends(get_file_service),
) -> FileResponse:
    try:
        file_path = service.get_file(filename)
    except InvalidFilenameError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except FileNotAvailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream",
    )
