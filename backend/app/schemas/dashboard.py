"""Schemas de dashboard."""

from pydantic import BaseModel, Field

from app.schemas.friend import FriendRead


class DashboardSummary(BaseModel):
    """Blocos principais do dashboard."""

    total_friends: int
    overdue_count: int
    total_interests: int
    average_temperature: int
    friends_by_temperature: list[FriendRead] = Field(default_factory=list)
    overdue_friends: list[FriendRead] = Field(default_factory=list)


class InterestCluster(BaseModel):
    """Agrupamento de amigos por interesse compartilhado."""

    tag: str
    friends: list[FriendRead] = Field(default_factory=list)


class DashboardOverdueResponse(BaseModel):
    """Resposta do endpoint `GET /api/dashboard/overdue`."""

    friends: list[FriendRead] = Field(default_factory=list)


class DashboardClustersResponse(BaseModel):
    """Resposta do endpoint `GET /api/dashboard/clusters`."""

    clusters: list[InterestCluster] = Field(default_factory=list)
