from fastapi import APIRouter

from app.api.routes import files, health, root

api_router = APIRouter()
api_router.include_router(root.router)
api_router.include_router(health.router)
api_router.include_router(files.router, prefix="/api/v1")
