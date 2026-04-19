"""Model exports.

Importar todos os modelos aqui garante que `Base.metadata` os enxergue no
lifespan do FastAPI e nas migrations do Alembic.
"""

from app.models.calendar_link import CalendarLink, CalendarProvider
from app.models.friend import Cadence, Category, Friend
from app.models.friend_tag import FriendTag
from app.models.interaction import Interaction, InteractionType
from app.models.sync_event import (
    SyncAction,
    SyncEntityType,
    SyncEvent,
    SyncProvider,
    SyncStatus,
)

__all__ = [
    "Cadence",
    "CalendarLink",
    "CalendarProvider",
    "Category",
    "Friend",
    "FriendTag",
    "Interaction",
    "InteractionType",
    "SyncAction",
    "SyncEntityType",
    "SyncEvent",
    "SyncProvider",
    "SyncStatus",
]
