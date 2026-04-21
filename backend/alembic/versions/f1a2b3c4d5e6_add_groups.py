"""add groups

Revision ID: f1a2b3c4d5e6
Revises: 85924c308070
Create Date: 2026-04-21 10:00:00.000000

Introduz `groups` (entidade de primeira classe) + `friend_group` (junction).
Coexiste com `friend_tag`; grupos sao listas curadas com nome unico, cor e
descricao; tags continuam servindo pra atributos livres.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "85924c308070"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "color",
            sa.String(length=16),
            nullable=False,
            server_default="#64748b",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_groups_name"),
    )
    op.create_index(op.f("ix_groups_name"), "groups", ["name"], unique=False)

    op.create_table(
        "friend_group",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("friend_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["friend_id"], ["friend.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["group_id"], ["groups.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "friend_id", "group_id", name="uq_friend_group_friend_group"
        ),
    )
    op.create_index(
        op.f("ix_friend_group_friend_id"),
        "friend_group",
        ["friend_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_friend_group_group_id"),
        "friend_group",
        ["group_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_friend_group_group_id"), table_name="friend_group")
    op.drop_index(op.f("ix_friend_group_friend_id"), table_name="friend_group")
    op.drop_table("friend_group")
    op.drop_index(op.f("ix_groups_name"), table_name="groups")
    op.drop_table("groups")
