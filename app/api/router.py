from fastapi import APIRouter

from app.api.routes import (
    admin,
    admin_analytics,
    admin_payload_config,
    analytics,
    contact,
    files,
    health,
    payload_config,
    root,
)

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(contact.router, prefix="/api/v1")
api_router.include_router(analytics.router, prefix="/api/v1")
api_router.include_router(payload_config.router, prefix="/api/v1")
api_router.include_router(files.router, prefix="/api/v1")
api_router.include_router(admin.router)
api_router.include_router(admin_analytics.router)
api_router.include_router(admin_payload_config.router)
