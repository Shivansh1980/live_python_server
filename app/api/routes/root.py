from fastapi import APIRouter

router = APIRouter(tags=["service"])


@router.get("/", summary="Describe the service")
def service_information() -> dict[str, str]:
    return {
        "service": "curvaturetech-api",
        "health": "/health",
        "files": "/api/v1/files",
        "contact": "/api/v1/contact",
        "admin": "/admin",
        "documentation": "/docs",
    }
