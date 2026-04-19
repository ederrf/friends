"""Router de dashboard (13.8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.dashboard import (
    DashboardClustersResponse,
    DashboardOverdueResponse,
    DashboardSummary,
)
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    session: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    return await dashboard_service.get_summary(session)


@router.get("/overdue", response_model=DashboardOverdueResponse)
async def get_overdue(
    session: AsyncSession = Depends(get_db),
) -> DashboardOverdueResponse:
    return await dashboard_service.get_overdue(session)


@router.get("/clusters", response_model=DashboardClustersResponse)
async def get_clusters(
    session: AsyncSession = Depends(get_db),
) -> DashboardClustersResponse:
    return await dashboard_service.get_clusters(session)
