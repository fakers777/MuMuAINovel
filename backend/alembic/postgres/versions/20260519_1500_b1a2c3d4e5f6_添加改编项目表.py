"""添加改编项目表

Revision ID: b1a2c3d4e5f6
Revises: acdb1d611064
Create Date: 2026-05-19 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1a2c3d4e5f6'
down_revision: Union[str, None] = 'acdb1d611064'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'adaptation_projects',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('workflow_mode', sa.String(length=20), nullable=False, comment='工作流类型，当前仅 adaptation'),
        sa.Column('workflow_status', sa.String(length=30), nullable=False, comment='工作流状态: planning/confirmed/materialized/generating/writing'),
        sa.Column('source_filename', sa.String(length=255), nullable=True, comment='原始导入文件名'),
        sa.Column('source_chapter_count', sa.Integer(), nullable=True, comment='原始章节数'),
        sa.Column('source_word_count', sa.Integer(), nullable=True, comment='原始总字数'),
        sa.Column('planned_outline_count', sa.Integer(), nullable=True, comment='当前已规划的大纲数'),
        sa.Column('target_age', sa.Integer(), nullable=True, comment='目标阅读年龄'),
        sa.Column('enforce_chronological', sa.Boolean(), nullable=False, comment='是否强制按时间顺序改写'),
        sa.Column('strict_fidelity', sa.Boolean(), nullable=False, comment='是否严格保持关键情节和结局'),
        sa.Column('compress_romance', sa.Boolean(), nullable=False, comment='是否适度压缩情爱描写'),
        sa.Column('outline_batch_size', sa.Integer(), nullable=False, comment='大纲生成批大小'),
        sa.Column('confirmed_at', sa.DateTime(), nullable=True, comment='大纲确认时间'),
        sa.Column('materialized_at', sa.DateTime(), nullable=True, comment='占位章节物化时间'),
        sa.Column('generation_started_at', sa.DateTime(), nullable=True, comment='首次正文生成时间'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True, comment='更新时间'),
        sa.CheckConstraint("workflow_mode IN ('adaptation')", name='check_adaptation_workflow_mode'),
        sa.CheckConstraint("workflow_status IN ('planning', 'confirmed', 'materialized', 'generating', 'writing')", name='check_adaptation_workflow_status'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_adaptation_projects_project_id'), 'adaptation_projects', ['project_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_adaptation_projects_project_id'), table_name='adaptation_projects')
    op.drop_table('adaptation_projects')
