"""原著改编工作流 API"""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.settings import get_user_ai_service_from_db
from app.database import get_db
from app.schemas.original_novel_adaptation import (
    AdaptationBatchConfirmResponse,
    AdaptationBriefSaveResponse,
    AdaptationBriefUpdateRequest,
    AdaptationChapterGenerateResponse,
    AdaptationGenerateChapterRequest,
    AdaptationPlanningBatchResponse,
    AdaptationPlanBatchRequest,
    AdaptationProjectCreateResponse,
    AdaptationProjectDetailResponse,
    AdaptationProjectListItem,
)
from app.services.original_novel_adaptation_service import original_novel_adaptation_service

router = APIRouter(prefix="/original-novel-adaptation", tags=["原著改编"])

MAX_TXT_SIZE = 80 * 1024 * 1024


@router.post("/projects", response_model=AdaptationProjectCreateResponse, summary="创建原著改编项目")
async def create_adaptation_project(
    request: Request,
    file: UploadFile = File(..., description="原著 TXT 文件"),
    title: str | None = Form(default=None, description="项目标题"),
    description: str | None = Form(default=None, description="项目描述"),
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    if not file.filename or not file.filename.lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="仅支持 TXT 原著文件")

    content = await file.read()
    if len(content) > MAX_TXT_SIZE:
        raise HTTPException(status_code=413, detail="文件大小超过 80MB 限制")
    await file.seek(0)
    return await original_novel_adaptation_service.create_project(
        user_id=user_id,
        db=db,
        file=file,
        title=title,
        description=description,
    )


@router.get("/projects", response_model=list[AdaptationProjectListItem], summary="获取原著改编项目列表")
async def list_adaptation_projects(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return await original_novel_adaptation_service.list_projects(user_id=user_id, db=db)


@router.get("/projects/{adaptation_project_id}", response_model=AdaptationProjectDetailResponse, summary="获取原著改编项目详情")
async def get_adaptation_project_detail(
    adaptation_project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return await original_novel_adaptation_service.get_project_detail(
        adaptation_project_id=adaptation_project_id,
        user_id=user_id,
        db=db,
    )


@router.put("/projects/{adaptation_project_id}/brief", response_model=AdaptationBriefSaveResponse, summary="保存自由提示词")
async def save_adaptation_brief(
    adaptation_project_id: str,
    payload: AdaptationBriefUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return await original_novel_adaptation_service.save_brief(
        adaptation_project_id=adaptation_project_id,
        user_id=user_id,
        db=db,
        brief_text=payload.brief_text,
        example_template=payload.example_template,
    )


@router.post("/projects/{adaptation_project_id}/plan-batch", response_model=AdaptationPlanningBatchResponse, summary="规划下一批章节")
async def plan_next_adaptation_batch(
    adaptation_project_id: str,
    payload: AdaptationPlanBatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    ai_service = await get_user_ai_service_from_db(user_id, db)
    return await original_novel_adaptation_service.plan_next_batch(
        adaptation_project_id=adaptation_project_id,
        user_id=user_id,
        db=db,
        batch_size=payload.batch_size,
        ai_service=ai_service,
    )


@router.post("/projects/{adaptation_project_id}/batches/{batch_id}/confirm", response_model=AdaptationBatchConfirmResponse, summary="确认当前批次并物化")
async def confirm_adaptation_batch(
    adaptation_project_id: str,
    batch_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return await original_novel_adaptation_service.confirm_batch(
        adaptation_project_id=adaptation_project_id,
        batch_id=batch_id,
        user_id=user_id,
        db=db,
    )


@router.post("/projects/{adaptation_project_id}/generate-chapter", response_model=AdaptationChapterGenerateResponse, summary="生成或重写某个已确认章节正文")
async def generate_adaptation_chapter(
    adaptation_project_id: str,
    payload: AdaptationGenerateChapterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    ai_service = await get_user_ai_service_from_db(user_id, db)
    return await original_novel_adaptation_service.generate_chapter(
        adaptation_project_id=adaptation_project_id,
        batch_item_id=payload.batch_item_id,
        chapter_id=payload.chapter_id,
        regenerate=payload.regenerate,
        user_id=user_id,
        db=db,
        ai_service=ai_service,
    )
