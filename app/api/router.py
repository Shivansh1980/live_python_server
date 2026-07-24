from fastapi import APIRouter

from app.api.routes import admin, contact, files, health, root

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(contact.router, prefix="/api/v1")
api_router.include_router(files.router, prefix="/api/v1")
api_router.include_router(admin.router)
