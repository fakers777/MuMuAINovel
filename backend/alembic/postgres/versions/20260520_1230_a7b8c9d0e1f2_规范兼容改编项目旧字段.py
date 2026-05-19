"""规范兼容改编项目旧字段

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-05-20 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())
    if "adaptation_projects" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("adaptation_projects")}
    if "workflow_mode" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN workflow_mode SET DEFAULT 'adaptation'")
        op.execute("UPDATE adaptation_projects SET workflow_mode = 'adaptation' WHERE workflow_mode IS NULL")
    if "enforce_chronological" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN enforce_chronological SET DEFAULT true")
        op.execute("UPDATE adaptation_projects SET enforce_chronological = true WHERE enforce_chronological IS NULL")
    if "strict_fidelity" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN strict_fidelity SET DEFAULT true")
        op.execute("UPDATE adaptation_projects SET strict_fidelity = true WHERE strict_fidelity IS NULL")
    if "compress_romance" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN compress_romance SET DEFAULT true")
        op.execute("UPDATE adaptation_projects SET compress_romance = true WHERE compress_romance IS NULL")
    if "outline_batch_size" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN outline_batch_size SET DEFAULT 5")
        op.execute("UPDATE adaptation_projects SET outline_batch_size = 5 WHERE outline_batch_size IS NULL")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())
    if "adaptation_projects" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("adaptation_projects")}
    if "workflow_mode" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN workflow_mode DROP DEFAULT")
    if "enforce_chronological" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN enforce_chronological DROP DEFAULT")
    if "strict_fidelity" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN strict_fidelity DROP DEFAULT")
    if "compress_romance" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN compress_romance DROP DEFAULT")
    if "outline_batch_size" in existing_columns:
        op.execute("ALTER TABLE adaptation_projects ALTER COLUMN outline_batch_size DROP DEFAULT")
