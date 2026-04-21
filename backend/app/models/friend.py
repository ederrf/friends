"""Friend model and related enums."""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Date, DateTime, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(StrEnum):
    """Categoria de uma amizade segundo o PRD secao 7.1."""

    REKINDLE = "rekindle"
    UPGRADE = "upgrade"
    MAINTAIN = "maintain"


class Cadence(StrEnum):
    """Cadencia alvo de contato segundo o PRD secao 7.2."""

    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class Friend(Base):
    """Amigo registrado no Friends."""

    __tablename__ = "friend"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    category: Mapped[Category] = mapped_column(
        SAEnum(Category, values_callable=lambda e: [m.value for m in e]),
        index=True,
        nullable=False,
    )
    cadence: Mapped[Cadence] = mapped_column(
        SAEnum(Cadence, values_callable=lambda e: [m.value for m in e]),
        index=True,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Nullable: amigo recem-criado pode nao ter contato registrado ainda.
    last_contact_at: Mapped[datetime | None] = mapped_column(
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

    tags: Mapped[list["FriendTag"]] = relationship(  # noqa: F821
        back_populates="friend",
        cascade="all, delete-orphan",
    )
    groups: Mapped[list["FriendGroup"]] = relationship(  # noqa: F821
        back_populates="friend",
        cascade="all, delete-orphan",
    )
    interactions: Mapped[list["Interaction"]] = relationship(  # noqa: F821
        back_populates="friend",
        cascade="all, delete-orphan",
        order_by="Interaction.occurred_at.desc()",
    )
    calendar_links: Mapped[list["CalendarLink"]] = relationship(  # noqa: F821
        back_populates="friend",
        cascade="all, delete-orphan",
    )
