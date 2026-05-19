"""扩展改编工作流状态约束

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-05-20 13:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("adaptation_projects", recreate="always") as batch_op:
        batch_op.drop_constraint("check_adaptation_workflow_status", type_="check")
        batch_op.create_check_constraint(
            "check_adaptation_workflow_status",
            "workflow_status IN ("
            "'planning', 'confirmed', 'materialized', 'generating', 'writing', "
            "'source_uploaded', 'brief_saved', 'batch_planning', 'batch_draft_ready', "
            "'batch_confirmed', 'batch_generating', 'batch_written'"
            ")",
        )


def downgrade() -> None:
    with op.batch_alter_table("adaptation_projects", recreate="always") as batch_op:
        batch_op.drop_constraint("check_adaptation_workflow_status", type_="check")
        batch_op.create_check_constraint(
            "check_adaptation_workflow_status",
            "workflow_status IN ("
            "'planning', 'confirmed', 'materialized', 'generating', 'writing'"
            ")",
        )
