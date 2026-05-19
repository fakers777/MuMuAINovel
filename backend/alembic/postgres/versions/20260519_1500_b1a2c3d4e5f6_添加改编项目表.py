"""兼容旧版改编项目迁移标记

Revision ID: b1a2c3d4e5f6
Revises: acdb1d611064
Create Date: 2026-05-19 15:00:00.000000
"""

from alembic import op


revision = "b1a2c3d4e5f6"
down_revision = "acdb1d611064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Compatibility placeholder for databases that were migrated with an
    # earlier fork-only adaptation revision.
    pass


def downgrade() -> None:
    pass
