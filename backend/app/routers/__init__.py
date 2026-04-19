"""Router exports."""

from app.routers.dashboard import router as dashboard_router
from app.routers.friends import router as friends_router
from app.routers.import_ import router as import_router
from app.routers.interactions import router as interactions_router
from app.routers.interests import interests_router, tags_router

__all__ = [
    "dashboard_router",
    "friends_router",
    "import_router",
    "interactions_router",
    "interests_router",
    "tags_router",
]
