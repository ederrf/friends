"""Interaction model."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InteractionType(StrEnum):
    """Tipo de interacao registrada."""

    MESSAGE = "message"
    CALL = "call"
    IN_PERSON = "in_person"
    EMAIL = "email"
    OTHER = "other"


class Interaction(Base):
    """Registro de uma interacao com um amigo."""

    __tablename__ = "interaction"
    __table_args__ = (
        Index("ix_interaction_friend_occurred", "friend_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    friend_id: Mapped[int] = mapped_column(
        ForeignKey("friend.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    interaction_type: Mapped[InteractionType] = mapped_column(
        SAEnum(InteractionType, values_callable=lambda e: [m.value for m in e]),
        default=InteractionType.OTHER,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    friend: Mapped["Friend"] = relationship(back_populates="interactions")  # noqa: F821
