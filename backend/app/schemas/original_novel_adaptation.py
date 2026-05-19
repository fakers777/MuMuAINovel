"""原著改编工作流 Schema"""
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AdaptationWorkflowStatus = Literal[
    "source_uploaded",
    "brief_saved",
    "batch_planning",
    "batch_draft_ready",
    "batch_confirmed",
    "batch_generating",
    "batch_written",
]
AdaptationBatchStatus = Literal["draft", "confirmed", "superseded", "cancelled"]
CanonAuditType = Literal["planning", "generation"]


class AdaptationBriefUpdateRequest(BaseModel):
    brief_text: str = Field(..., min_length=1, description="自由提示词")
    example_template: Optional[str] = Field(None, description="示例模板标识，仅用于回填辅助文本")


class AdaptationPlanBatchRequest(BaseModel):
    batch_size: int = Field(..., ge=1, le=20, description="本次规划章节数")


class AdaptationGenerateChapterRequest(BaseModel):
    chapter_id: str = Field(..., description="共享章节ID")
    batch_item_id: str = Field(..., description="批次项ID")
    regenerate: bool = Field(default=False, description="是否重新生成当前章节正文")


class AdaptationBatchItemResponse(BaseModel):
    id: str
    item_index: int
    proposed_title: str
    proposed_outline: str
    source_chunk_ids: list[str]
    source_span_start: Optional[int] = None
    source_span_end: Optional[int] = None
    notes: Optional[str] = None
    materialized_outline_id: Optional[str] = None
    materialized_chapter_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdaptationPlanningBatchResponse(BaseModel):
    id: str
    batch_number: int
    requested_batch_size: int
    brief_version: int
    status: AdaptationBatchStatus
    batch_summary: Optional[str] = None
    retrieval_summary: Optional[dict[str, Any]] = None
    confirmed_at: Optional[datetime] = None
    items: list[AdaptationBatchItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdaptationCanonAuditResponse(BaseModel):
    id: str
    audit_type: CanonAuditType
    batch_id: Optional[str] = None
    batch_item_id: Optional[str] = None
    target_chapter_id: Optional[str] = None
    brief_version: Optional[int] = None
    retrieved_chunk_ids: list[str]
    provenance: list[dict[str, Any]]
    confirmed_batch_refs: list[dict[str, Any]]
    contradiction_results: dict[str, Any]
    summary: Optional[str] = None
    raw_payload: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdaptationProjectCreateResponse(BaseModel):
    adaptation_project_id: str
    project_id: str
    title: str
    workflow_status: AdaptationWorkflowStatus
    source_filename: str
    total_characters: int
    total_chunks: int


class AdaptationProjectListItem(BaseModel):
    adaptation_project_id: str
    project_id: str
    title: str
    workflow_status: AdaptationWorkflowStatus
    source_filename: str
    brief_version: Optional[int] = None
    latest_batch_number: int = 0
    confirmed_batch_count: int = 0
    created_at: datetime
    updated_at: datetime


class AdaptationProjectDetailResponse(BaseModel):
    adaptation_project_id: str
    project_id: str
    title: str
    description: Optional[str] = None
    workflow_status: AdaptationWorkflowStatus
    source_filename: str
    total_characters: int
    total_chunks: int
    active_brief_text: Optional[str] = None
    active_brief_version: Optional[int] = None
    example_template: Optional[str] = None
    draft_batch: Optional[AdaptationPlanningBatchResponse] = None
    confirmed_batches: list[AdaptationPlanningBatchResponse] = Field(default_factory=list)
    recent_audits: list[AdaptationCanonAuditResponse] = Field(default_factory=list)
    can_edit_brief: bool = True
    can_plan_next_batch: bool = True
    created_at: datetime
    updated_at: datetime


class AdaptationBriefSaveResponse(BaseModel):
    adaptation_project_id: str
    version: int
    brief_text: str
    example_template: Optional[str] = None
    workflow_status: AdaptationWorkflowStatus


class AdaptationBatchConfirmResponse(BaseModel):
    success: bool
    adaptation_project_id: str
    batch_id: str
    materialized_count: int
    project_id: str


class AdaptationChapterGenerateResponse(BaseModel):
    success: bool
    project_id: str
    chapter_id: str
    title: str
    word_count: int
    audit_id: str
