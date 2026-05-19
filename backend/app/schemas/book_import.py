"""拆书导入相关的 Pydantic Schema"""
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


TaskStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
ImportMode = Literal["append", "overwrite"]
ExtractLevel = Literal["basic", "standard", "deep"]
WarningLevel = Literal["info", "warning", "error"]
BookImportExtractMode = Literal["tail", "full"]
BookImportWorkflowMode = Literal["standard", "adaptation"]


class AdaptationConfig(BaseModel):
    """改写模式配置"""
    target_age: int = Field(default=12, ge=8, le=18, description="目标阅读年龄")
    enforce_chronological: bool = Field(default=True, description="是否按时间顺序重写")
    strict_fidelity: bool = Field(default=True, description="是否严格保持关键情节和结局")
    compress_romance: bool = Field(default=True, description="是否压缩情爱描写但保留关系关键内容")
    outline_batch_size: int = Field(default=5, ge=1, le=20, description="大纲规划批大小")


class BookImportWarning(BaseModel):
    """导入告警信息"""
    code: str = Field(..., description="告警编码")
    message: str = Field(..., description="告警内容")
    level: WarningLevel = Field(default="warning", description="告警等级")


class ProjectSuggestion(BaseModel):
    """项目建议信息（可在预览页修改）"""
    title: str = Field(..., min_length=1, max_length=200, description="项目标题")
    description: Optional[str] = Field(None, description="项目简介")
    theme: Optional[str] = Field(None, description="主题")
    genre: Optional[str] = Field(None, description="类型")
    narrative_perspective: str = Field(default="第三人称", description="叙事视角")
    target_words: int = Field(default=100000, ge=1000, description="目标字数（默认10万字）")


class BookImportChapter(BaseModel):
    """预览章节"""
    title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    content: str = Field(default="", description="章节正文")
    summary: Optional[str] = Field(None, description="章节摘要")
    chapter_number: int = Field(..., ge=1, description="章节序号")
    outline_title: Optional[str] = Field(None, description="关联大纲标题（可选）")


class BookImportOutline(BaseModel):
    """预览大纲"""
    title: str = Field(..., min_length=1, max_length=200, description="大纲标题")
    content: Optional[str] = Field(None, description="大纲内容")
    order_index: int = Field(..., ge=1, description="排序序号")
    structure: Optional[dict[str, Any]] = Field(None, description="结构化大纲（与系统大纲生成结构一致）")


class BookImportTaskCreateRequest(BaseModel):
    """创建拆书任务请求"""
    workflow_mode: BookImportWorkflowMode = Field(default="standard", description="工作流模式")
    extract_mode: BookImportExtractMode = Field(default="tail", description="提取范围：tail=截取末章，full=整本")
    tail_chapter_count: int = Field(default=10, ge=5, le=9999, description="当 extract_mode=tail 时，截取末尾章节数；需为5的倍数，超过50将按整本处理")
    adaptation_config: Optional[AdaptationConfig] = Field(default=None, description="改写模式配置")


class BookImportTaskCreateResponse(BaseModel):
    """创建任务响应"""
    task_id: str
    status: TaskStatus
    workflow_mode: BookImportWorkflowMode = "standard"


class BookImportTaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: TaskStatus
    workflow_mode: BookImportWorkflowMode = "standard"
    progress: int = Field(..., ge=0, le=100)
    message: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BookImportPreviewResponse(BaseModel):
    """预览数据响应"""
    task_id: str
    workflow_mode: BookImportWorkflowMode = "standard"
    project_suggestion: ProjectSuggestion
    chapters: list[BookImportChapter]
    outlines: list[BookImportOutline]
    warnings: list[BookImportWarning]


class BookImportApplyRequest(BaseModel):
    """确认导入请求（支持前端修订后的数据）"""
    project_suggestion: ProjectSuggestion
    chapters: list[BookImportChapter]
    outlines: list[BookImportOutline] = Field(default_factory=list)
    import_mode: ImportMode = Field(default="append", description="导入模式")


class BookImportApplyResponse(BaseModel):
    """确认导入响应"""
    success: bool
    project_id: str
    workflow_mode: BookImportWorkflowMode = "standard"
    next_route: Optional[str] = None
    statistics: dict[str, int]
    warnings: list[BookImportWarning] = Field(default_factory=list)


class BookImportRetryRequest(BaseModel):
    """重试失败步骤请求"""
    steps: list[str] = Field(..., min_length=1, description="需要重试的步骤名列表，如 world_building / career_system / characters")
