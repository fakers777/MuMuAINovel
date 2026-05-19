"""原著改编工作流数据模型"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database import Base
import uuid


class AdaptationProject(Base):
    """原著改编项目主表"""

    __tablename__ = "adaptation_projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    user_id = Column(String(100), nullable=False, index=True, comment="用户ID")
    workflow_status = Column(String(32), nullable=False, default="source_uploaded", comment="工作流状态")
    source_corpus_status = Column(String(32), nullable=False, default="ready", comment="原著语料状态")
    active_batch_id = Column(String(36), ForeignKey("adaptation_planning_batches.id", ondelete="SET NULL"), nullable=True)
    last_confirmed_batch_id = Column(String(36), ForeignKey("adaptation_planning_batches.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class AdaptationSourceCorpus(Base):
    """原著全文和切块信息"""

    __tablename__ = "adaptation_source_corpora"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    adaptation_project_id = Column(String(36), ForeignKey("adaptation_projects.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    filename = Column(String(255), nullable=False, comment="原始文件名")
    content_type = Column(String(100), nullable=True, comment="文件类型")
    file_size = Column(Integer, nullable=False, default=0, comment="文件大小")
    total_characters = Column(Integer, nullable=False, default=0, comment="全文字符数")
    total_chunks = Column(Integer, nullable=False, default=0, comment="切块数")
    full_text = Column(Text, nullable=False, comment="原著全文")
    chunk_manifest = Column(JSON, nullable=False, comment="切块清单")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class AdaptationBrief(Base):
    """自由提示词版本表"""

    __tablename__ = "adaptation_briefs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    adaptation_project_id = Column(String(36), ForeignKey("adaptation_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, comment="提示词版本号")
    brief_text = Column(Text, nullable=False, comment="自由提示词")
    example_template = Column(String(100), nullable=True, comment="仅用于辅助展示的示例模板标识")
    is_active = Column(Boolean, nullable=False, default=True, comment="是否当前激活版本")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    __table_args__ = (
        UniqueConstraint("adaptation_project_id", "version", name="uq_adaptation_brief_project_version"),
    )


class AdaptationPlanningBatch(Base):
    """批次规划主表"""

    __tablename__ = "adaptation_planning_batches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    adaptation_project_id = Column(String(36), ForeignKey("adaptation_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_number = Column(Integer, nullable=False, comment="第几批")
    requested_batch_size = Column(Integer, nullable=False, comment="用户请求批量")
    brief_version = Column(Integer, nullable=False, comment="规划时使用的提示词版本")
    status = Column(String(24), nullable=False, default="draft", comment="draft/confirmed/superseded/cancelled")
    batch_summary = Column(Text, nullable=True, comment="批次总结")
    retrieval_summary = Column(JSON, nullable=True, comment="检索上下文摘要")
    confirmed_at = Column(DateTime, nullable=True, comment="确认时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    __table_args__ = (
        UniqueConstraint("adaptation_project_id", "batch_number", name="uq_adaptation_batch_project_number"),
    )


class AdaptationBatchItem(Base):
    """批次内的候选章节项"""

    __tablename__ = "adaptation_batch_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    batch_id = Column(String(36), ForeignKey("adaptation_planning_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    item_index = Column(Integer, nullable=False, comment="批次内顺序")
    proposed_title = Column(String(255), nullable=False, comment="建议章节标题")
    proposed_outline = Column(Text, nullable=False, comment="建议大纲")
    source_chunk_ids = Column(JSON, nullable=False, comment="关联原著切块ID")
    source_span_start = Column(Integer, nullable=True, comment="建议起始偏移")
    source_span_end = Column(Integer, nullable=True, comment="建议结束偏移")
    notes = Column(Text, nullable=True, comment="额外说明")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    __table_args__ = (
        UniqueConstraint("batch_id", "item_index", name="uq_adaptation_batch_item_order"),
    )


class AdaptationCanonAudit(Base):
    """规划/生成的原著校验审计"""

    __tablename__ = "adaptation_canon_audits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    adaptation_project_id = Column(String(36), ForeignKey("adaptation_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(String(36), ForeignKey("adaptation_planning_batches.id", ondelete="CASCADE"), nullable=True, index=True)
    batch_item_id = Column(String(36), ForeignKey("adaptation_batch_items.id", ondelete="SET NULL"), nullable=True, index=True)
    target_chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True, index=True)
    audit_type = Column(String(24), nullable=False, comment="planning/generation")
    brief_version = Column(Integer, nullable=True, comment="使用的提示词版本")
    retrieved_chunk_ids = Column(JSON, nullable=False, comment="检索到的切块ID")
    provenance = Column(JSON, nullable=False, comment="切块溯源与偏移")
    confirmed_batch_refs = Column(JSON, nullable=False, comment="引用的已确认批次")
    contradiction_results = Column(JSON, nullable=False, comment="冲突校验结果")
    summary = Column(Text, nullable=True, comment="审计摘要")
    raw_payload = Column(JSON, nullable=True, comment="调试载荷")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")


class AdaptationMaterializationMap(Base):
    """批次项到共享大纲/章节的映射"""

    __tablename__ = "adaptation_materialization_maps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    adaptation_project_id = Column(String(36), ForeignKey("adaptation_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(String(36), ForeignKey("adaptation_planning_batches.id", ondelete="CASCADE"), nullable=False, index=True)
    batch_item_id = Column(String(36), ForeignKey("adaptation_batch_items.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    outline_id = Column(String(36), ForeignKey("outlines.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_id = Column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
