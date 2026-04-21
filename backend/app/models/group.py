"""Group and FriendGroup models (13.23).

Group e uma colecao curada de amigos com identidade propria (nome unico,
descricao opcional, cor pra UI). Coexiste com FriendTag: tags sao strings
livres, grupos sao entidades de primeira classe.

Tabela e nomeada `groups` (pluralizada) porque `group` e palavra
reservada do SQL; evita conflito em qualquer dialeto.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Group(Base):
    """Grupo curado de amigos."""

    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(
        String(80), unique=True, index=True, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Hex color #RRGGBB normalizado pra lowercase. Default = slate-500.
    color: Mapped[str] = mapped_column(
        String(16), nullable=False, default="#64748b"
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

    members: Mapped[list["FriendGroup"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )


class FriendGroup(Base):
    """Junction entre Friend e Group (many-to-many)."""

    __tablename__ = "friend_group"
    __table_args__ = (
        UniqueConstraint(
            "friend_id", "group_id", name="uq_friend_group_friend_group"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    friend_id: Mapped[int] = mapped_column(
        ForeignKey("friend.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    friend: Mapped["Friend"] = relationship(back_populates="groups")  # noqa: F821
    group: Mapped["Group"] = relationship(back_populates="members")
