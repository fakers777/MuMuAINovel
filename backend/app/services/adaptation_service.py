"""改写项目共享服务"""
from __future__ import annotations

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.adaptation_project import AdaptationProject
from app.models.project import Project


class AdaptationService:
    @staticmethod
    async def get_state(db: AsyncSession, project_id: str) -> Optional[AdaptationProject]:
        result = await db.execute(
            select(AdaptationProject).where(AdaptationProject.project_id == project_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def build_instruction_block(state: Optional[AdaptationProject]) -> str:
        if not state:
            return ""

        chronology = "必须按故事时间顺序组织内容" if state.enforce_chronological else "不强制时间顺序"
        fidelity = "关键事件、人物关系、结局不得改动" if state.strict_fidelity else "尽量保持原著关键情节"
        romance = "可以适度压缩情爱描写，但不得删除影响关系判断的信息" if state.compress_romance else "保留原有人物情感推进"

        return (
            "【改写项目硬性约束】\n"
            f"- 目标读者：约 {state.target_age} 岁\n"
            f"- {chronology}\n"
            f"- {fidelity}\n"
            f"- {romance}\n"
            "- 语言需更直白、易读，避免过于复杂的句式和成人化表达\n"
            "- 如果当前章节大纲与这些约束冲突，以这些约束和已确认大纲为准\n"
        )

    @staticmethod
    async def mark_generation_started(
        db: AsyncSession,
        *,
        state: Optional[AdaptationProject],
        project: Optional[Project] = None,
    ) -> None:
        if not state:
            return

        if state.generation_started_at is None:
            from datetime import datetime

            state.generation_started_at = datetime.utcnow()
            state.workflow_status = "generating"

        if project and project.status != "writing":
            project.status = "writing"
