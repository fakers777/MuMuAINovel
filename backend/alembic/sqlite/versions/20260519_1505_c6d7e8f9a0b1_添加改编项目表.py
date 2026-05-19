"""添加改编项目表

Revision ID: c6d7e8f9a0b1
Revises: 3a08fc61773f
Create Date: 2026-05-19 15:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, None] = '3a08fc61773f'
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
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True, comment='更新时间'),
        sa.CheckConstraint("workflow_mode IN ('adaptation')", name='check_adaptation_workflow_mode'),
        sa.CheckConstraint("workflow_status IN ('planning', 'confirmed', 'materialized', 'generating', 'writing')", name='check_adaptation_workflow_status'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('adaptation_projects', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_adaptation_projects_project_id'), ['project_id'], unique=True)


def downgrade() -> None:
    with op.batch_alter_table('adaptation_projects', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_adaptation_projects_project_id'))

    op.drop_table('adaptation_projects')
