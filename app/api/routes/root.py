from fastapi import APIRouter

router = APIRouter(tags=["service"])


@router.get("/", summary="Describe the service")
def service_information() -> dict[str, str]:
    return {
        "service": "downloadable-files-api",
        "health": "/health",
        "files": "/api/v1/files",
        "documentation": "/docs",
    }
