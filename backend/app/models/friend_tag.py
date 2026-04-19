"""Friend tag / interest model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FriendTag(Base):
    """Tag ou interesse associado a um amigo."""

    __tablename__ = "friend_tag"
    __table_args__ = (
        UniqueConstraint("friend_id", "tag", name="uq_friend_tag_friend_tag"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    friend_id: Mapped[int] = mapped_column(
        ForeignKey("friend.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tag: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    friend: Mapped["Friend"] = relationship(back_populates="tags")  # noqa: F821
