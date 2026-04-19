"""Calendar link model.

Mapeia um amigo local a um evento externo de calendario (Google Calendar)
para permitir reagendar o lembrete apos cada nova interacao.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CalendarProvider(StrEnum):
    """Provedor de calendario suportado."""

    GOOGLE_CALENDAR = "google_calendar"


class CalendarLink(Base):
    """Liga amigo local a um evento externo de calendario."""

    __tablename__ = "calendar_link"
    __table_args__ = (
        UniqueConstraint(
            "friend_id", "provider", name="uq_calendar_link_friend_provider"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    friend_id: Mapped[int] = mapped_column(
        ForeignKey("friend.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    provider: Mapped[CalendarProvider] = mapped_column(
        SAEnum(CalendarProvider, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    external_event_id: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    friend: Mapped["Friend"] = relationship(back_populates="calendar_links")  # noqa: F821
