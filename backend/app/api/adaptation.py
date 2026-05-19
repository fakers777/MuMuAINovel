"""改写项目工作流 API"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import verify_project_access
from app.database import get_db
from app.models.adaptation_project import AdaptationProject
from app.models.chapter import Chapter
from app.models.outline import Outline
from app.models.project import Project
from app.schemas.adaptation import (
    AdaptationStateResponse,
    ConfirmAdaptationOutlinesResponse,
    ReopenAdaptationPlanResponse,
)
from app.services.adaptation_service import AdaptationService

router = APIRouter(prefix="/adaptation", tags=["adaptation"])


async def _build_state_response(
    *,
    db: AsyncSession,
    project: Project,
    state: AdaptationProject,
) -> AdaptationStateResponse:
    chapter_stats = await db.execute(
        select(func.count(Chapter.id), func.sum(func.length(func.coalesce(Chapter.content, ""))))
        .where(Chapter.project_id == project.id)
    )
    chapter_count, generated_chars = chapter_stats.one()
    has_generated_chapters = bool(chapter_count and (generated_chars or 0) > 0)
    can_reopen = state.workflow_status in {"confirmed", "materialized"} and not has_generated_chapters
    can_confirm = state.workflow_status == "planning"

    return AdaptationStateResponse(
        project_id=project.id,
        workflow_mode=state.workflow_mode,
        workflow_status=state.workflow_status,
        source_filename=state.source_filename,
        source_chapter_count=state.source_chapter_count or 0,
        source_word_count=state.source_word_count or 0,
        planned_outline_count=state.planned_outline_count or 0,
        target_age=state.target_age or 12,
        enforce_chronological=bool(state.enforce_chronological),
        strict_fidelity=bool(state.strict_fidelity),
        compress_romance=bool(state.compress_romance),
        outline_batch_size=state.outline_batch_size or 5,
        confirmed_at=state.confirmed_at,
        materialized_at=state.materialized_at,
        generation_started_at=state.generation_started_at,
        can_confirm=can_confirm,
        can_reopen=can_reopen,
        has_generated_chapters=has_generated_chapters,
    )


@router.get("/projects/{project_id}", response_model=AdaptationStateResponse)
async def get_adaptation_state(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    project = await verify_project_access(project_id, user_id, db)
    state = await AdaptationService.get_state(db, project_id)
    if not state:
        raise HTTPException(status_code=404, detail="该项目不是改写项目")
    return await _build_state_response(db=db, project=project, state=state)


@router.post("/projects/{project_id}/confirm-outlines", response_model=ConfirmAdaptationOutlinesResponse)
async def confirm_adaptation_outlines(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    project = await verify_project_access(project_id, user_id, db)
    state = await AdaptationService.get_state(db, project_id)
    if not state:
        raise HTTPException(status_code=404, detail="该项目不是改写项目")
    if state.workflow_status != "planning":
        raise HTTPException(status_code=400, detail="当前状态不允许确认大纲")

    outline_result = await db.execute(
        select(Outline)
        .where(Outline.project_id == project_id)
        .order_by(Outline.order_index.asc())
    )
    outlines = outline_result.scalars().all()
    if not outlines:
        raise HTTPException(status_code=400, detail="项目暂无可确认的大纲")

    existing_chapter_result = await db.execute(
        select(func.count(Chapter.id))
        .where(Chapter.project_id == project_id)
    )
    if (existing_chapter_result.scalar_one() or 0) > 0:
        raise HTTPException(status_code=400, detail="项目已存在章节，无法重复物化")

    created_count = 0
    for index, outline in enumerate(outlines, start=1):
        db.add(Chapter(
            project_id=project_id,
            chapter_number=index,
            title=outline.title,
            content="",
            summary=outline.content,
            word_count=0,
            status="draft",
            outline_id=outline.id,
            sub_index=1,
        ))
        created_count += 1

    now = datetime.utcnow()
    state.confirmed_at = now
    state.materialized_at = now
    state.workflow_status = "materialized"
    state.planned_outline_count = len(outlines)
    project.chapter_count = len(outlines)
    project.current_words = 0

    await db.commit()

    return ConfirmAdaptationOutlinesResponse(
        project_id=project_id,
        chapter_count=created_count,
        workflow_status=state.workflow_status,
    )


@router.post("/projects/{project_id}/reopen-plan", response_model=ReopenAdaptationPlanResponse)
async def reopen_adaptation_plan(
    project_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = getattr(request.state, "user_id", None)
    project = await verify_project_access(project_id, user_id, db)
    state = await AdaptationService.get_state(db, project_id)
    if not state:
        raise HTTPException(status_code=404, detail="该项目不是改写项目")
    if state.workflow_status not in {"confirmed", "materialized"}:
        raise HTTPException(status_code=400, detail="当前状态不允许重开规划")

    chapters_result = await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id)
        .order_by(Chapter.chapter_number.asc())
    )
    chapters = chapters_result.scalars().all()
    if any((chapter.content or "").strip() for chapter in chapters):
        raise HTTPException(status_code=400, detail="已有章节正文生成，v1 不允许重开规划")

    removed_placeholder_chapters = len(chapters)
    if removed_placeholder_chapters:
        await db.execute(delete(Chapter).where(Chapter.project_id == project_id))

    state.workflow_status = "planning"
    state.confirmed_at = None
    state.materialized_at = None
    project.chapter_count = 0
    project.current_words = 0
    project.status = "planning"

    await db.commit()

    return ReopenAdaptationPlanResponse(
        project_id=project_id,
        workflow_status=state.workflow_status,
        removed_placeholder_chapters=removed_placeholder_chapters,
    )
