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
    with op.batch_alter_table("adaptation_projects") as batch_op:
        if "workflow_mode" in existing_columns:
            batch_op.alter_column("workflow_mode", existing_type=sa.String(length=20), server_default="adaptation")
        if "enforce_chronological" in existing_columns:
            batch_op.alter_column("enforce_chronological", existing_type=sa.Boolean(), server_default=sa.true())
        if "strict_fidelity" in existing_columns:
            batch_op.alter_column("strict_fidelity", existing_type=sa.Boolean(), server_default=sa.true())
        if "compress_romance" in existing_columns:
            batch_op.alter_column("compress_romance", existing_type=sa.Boolean(), server_default=sa.true())
        if "outline_batch_size" in existing_columns:
            batch_op.alter_column("outline_batch_size", existing_type=sa.Integer(), server_default="5")

    if "workflow_mode" in existing_columns:
        op.execute("UPDATE adaptation_projects SET workflow_mode = 'adaptation' WHERE workflow_mode IS NULL")
    if "enforce_chronological" in existing_columns:
        op.execute("UPDATE adaptation_projects SET enforce_chronological = 1 WHERE enforce_chronological IS NULL")
    if "strict_fidelity" in existing_columns:
        op.execute("UPDATE adaptation_projects SET strict_fidelity = 1 WHERE strict_fidelity IS NULL")
    if "compress_romance" in existing_columns:
        op.execute("UPDATE adaptation_projects SET compress_romance = 1 WHERE compress_romance IS NULL")
    if "outline_batch_size" in existing_columns:
        op.execute("UPDATE adaptation_projects SET outline_batch_size = 5 WHERE outline_batch_size IS NULL")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    table_names = set(inspector.get_table_names())
    if "adaptation_projects" not in table_names:
        return

    existing_columns = {column["name"] for column in inspector.get_columns("adaptation_projects")}
    with op.batch_alter_table("adaptation_projects") as batch_op:
        if "workflow_mode" in existing_columns:
            batch_op.alter_column("workflow_mode", existing_type=sa.String(length=20), server_default=None)
        if "enforce_chronological" in existing_columns:
            batch_op.alter_column("enforce_chronological", existing_type=sa.Boolean(), server_default=None)
        if "strict_fidelity" in existing_columns:
            batch_op.alter_column("strict_fidelity", existing_type=sa.Boolean(), server_default=None)
        if "compress_romance" in existing_columns:
            batch_op.alter_column("compress_romance", existing_type=sa.Boolean(), server_default=None)
        if "outline_batch_size" in existing_columns:
            batch_op.alter_column("outline_batch_size", existing_type=sa.Integer(), server_default=None)
