"""兼容旧版改编项目迁移标记

Revision ID: c6d7e8f9a0b1
Revises: 3a08fc61773f
Create Date: 2026-05-19 15:05:00.000000
"""

from alembic import op


revision = "c6d7e8f9a0b1"
down_revision = "3a08fc61773f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Compatibility placeholder for databases that were migrated with an
    # earlier fork-only adaptation revision.
    pass


def downgrade() -> None:
    pass
