"""改写项目相关 Schema"""
from datetime import datetime
from pydantic import BaseModel, Field


class AdaptationStateResponse(BaseModel):
    project_id: str
    workflow_mode: str
    workflow_status: str
    source_filename: str | None = None
    source_chapter_count: int = 0
    source_word_count: int = 0
    planned_outline_count: int = 0
    target_age: int = 12
    enforce_chronological: bool = True
    strict_fidelity: bool = True
    compress_romance: bool = True
    outline_batch_size: int = 5
    confirmed_at: datetime | None = None
    materialized_at: datetime | None = None
    generation_started_at: datetime | None = None
    can_confirm: bool = False
    can_reopen: bool = False
    has_generated_chapters: bool = False


class ConfirmAdaptationOutlinesResponse(BaseModel):
    success: bool = True
    project_id: str
    chapter_count: int = Field(..., description="本次物化的占位章节数")
    workflow_status: str


class ReopenAdaptationPlanResponse(BaseModel):
    success: bool = True
    project_id: str
    workflow_status: str
    removed_placeholder_chapters: int = 0
