"""改写项目工作流状态模型"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base
import uuid


class AdaptationProject(Base):
    """适配/改写项目状态表"""
    __tablename__ = "adaptation_projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    workflow_mode = Column(String(20), nullable=False, default="adaptation", comment="工作流类型，当前仅 adaptation")
    workflow_status = Column(
        String(30),
        nullable=False,
        default="planning",
        comment="工作流状态: planning/confirmed/materialized/generating/writing"
    )

    source_filename = Column(String(255), nullable=True, comment="原始导入文件名")
    source_chapter_count = Column(Integer, default=0, comment="原始章节数")
    source_word_count = Column(Integer, default=0, comment="原始总字数")
    planned_outline_count = Column(Integer, default=0, comment="当前已规划的大纲数")

    target_age = Column(Integer, default=12, comment="目标阅读年龄")
    enforce_chronological = Column(Boolean, default=True, nullable=False, comment="是否强制按时间顺序改写")
    strict_fidelity = Column(Boolean, default=True, nullable=False, comment="是否严格保持关键情节和结局")
    compress_romance = Column(Boolean, default=True, nullable=False, comment="是否适度压缩情爱描写")
    outline_batch_size = Column(Integer, default=5, nullable=False, comment="大纲生成批大小")

    confirmed_at = Column(DateTime, nullable=True, comment="大纲确认时间")
    materialized_at = Column(DateTime, nullable=True, comment="占位章节物化时间")
    generation_started_at = Column(DateTime, nullable=True, comment="首次正文生成时间")

    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        CheckConstraint(
            "workflow_mode IN ('adaptation')",
            name="check_adaptation_workflow_mode",
        ),
        CheckConstraint(
            "workflow_status IN ('planning', 'confirmed', 'materialized', 'generating', 'writing')",
            name="check_adaptation_workflow_status",
        ),
        {"extend_existing": True},
    )

    def __repr__(self):
        return f"<AdaptationProject(project_id={self.project_id}, status={self.workflow_status})>"
