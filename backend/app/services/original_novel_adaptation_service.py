"""原著改编工作流服务"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.models.chapter import Chapter
from app.models.original_novel_adaptation import (
    AdaptationBatchItem,
    AdaptationBrief,
    AdaptationCanonAudit,
    AdaptationMaterializationMap,
    AdaptationPlanningBatch,
    AdaptationProject,
    AdaptationSourceCorpus,
)
from app.models.outline import Outline
from app.models.project import Project
from app.schemas.original_novel_adaptation import (
    AdaptationBatchConfirmResponse,
    AdaptationBriefSaveResponse,
    AdaptationCanonAuditResponse,
    AdaptationChapterGenerateResponse,
    AdaptationPlanningBatchResponse,
    AdaptationProjectCreateResponse,
    AdaptationProjectDetailResponse,
    AdaptationProjectListItem,
)
from app.services.ai_service import AIService
from app.services.json_helper import parse_json

logger = get_logger(__name__)

CANON_CATEGORIES = [
    "key_plot_outcomes",
    "character_relationships",
    "worldbuilding",
    "organizations",
    "ending_direction",
]


class OriginalNovelAdaptationService:
    """原著改编工作流服务"""

    def _chunk_source_text(self, text: str, *, chunk_size: int = 2400, overlap: int = 250) -> list[dict[str, Any]]:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
        chunks: list[dict[str, Any]] = []
        if not normalized:
            return chunks

        start = 0
        chunk_index = 1
        total = len(normalized)
        while start < total:
            end = min(total, start + chunk_size)
            if end < total:
                window = normalized[start:end]
                split_at = max(window.rfind("\n\n"), window.rfind("\n"))
                if split_at > chunk_size // 2:
                    end = start + split_at
            content = normalized[start:end].strip()
            if content:
                chunks.append(
                    {
                        "chunk_id": f"chunk-{chunk_index:04d}",
                        "index": chunk_index,
                        "start_offset": start,
                        "end_offset": end,
                        "content": content,
                    }
                )
                chunk_index += 1
            if end >= total:
                break
            start = max(end - overlap, start + 1)
        return chunks

    def _guess_title(self, filename: str, text: str) -> str:
        stem = Path(filename).stem.strip()
        if stem:
            return stem[:200]
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "原著改编项目")
        return first_line[:200]

    async def _get_adaptation_project(self, db: AsyncSession, adaptation_project_id: str, user_id: str) -> tuple[AdaptationProject, Project]:
        result = await db.execute(
            select(AdaptationProject, Project)
            .join(Project, Project.id == AdaptationProject.project_id)
            .where(AdaptationProject.id == adaptation_project_id, AdaptationProject.user_id == user_id)
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="原著改编项目不存在")
        return row[0], row[1]

    async def _get_source_corpus(self, db: AsyncSession, adaptation_project_id: str) -> AdaptationSourceCorpus:
        result = await db.execute(
            select(AdaptationSourceCorpus).where(AdaptationSourceCorpus.adaptation_project_id == adaptation_project_id)
        )
        corpus = result.scalar_one_or_none()
        if not corpus:
            raise HTTPException(status_code=404, detail="原著语料不存在")
        return corpus

    async def _get_active_brief(self, db: AsyncSession, adaptation_project_id: str) -> Optional[AdaptationBrief]:
        result = await db.execute(
            select(AdaptationBrief)
            .where(
                AdaptationBrief.adaptation_project_id == adaptation_project_id,
                AdaptationBrief.is_active.is_(True),
            )
            .order_by(AdaptationBrief.version.desc())
        )
        return result.scalar_one_or_none()

    async def _get_batch_items(self, db: AsyncSession, batch_id: str) -> list[AdaptationBatchItem]:
        result = await db.execute(
            select(AdaptationBatchItem)
            .where(AdaptationBatchItem.batch_id == batch_id)
            .order_by(AdaptationBatchItem.item_index.asc())
        )
        return list(result.scalars().all())

    async def _get_materialization_map(self, db: AsyncSession, batch_id: str) -> dict[str, AdaptationMaterializationMap]:
        result = await db.execute(
            select(AdaptationMaterializationMap).where(AdaptationMaterializationMap.batch_id == batch_id)
        )
        rows = result.scalars().all()
        return {row.batch_item_id: row for row in rows}

    async def _serialize_batch(self, db: AsyncSession, batch: AdaptationPlanningBatch) -> AdaptationPlanningBatchResponse:
        items = await self._get_batch_items(db, batch.id)
        item_map = await self._get_materialization_map(db, batch.id)
        return AdaptationPlanningBatchResponse(
            id=batch.id,
            batch_number=batch.batch_number,
            requested_batch_size=batch.requested_batch_size,
            brief_version=batch.brief_version,
            status=batch.status,
            batch_summary=batch.batch_summary,
            retrieval_summary=batch.retrieval_summary,
            confirmed_at=batch.confirmed_at,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
            items=[
                {
                    "id": item.id,
                    "item_index": item.item_index,
                    "proposed_title": item.proposed_title,
                    "proposed_outline": item.proposed_outline,
                    "source_chunk_ids": item.source_chunk_ids or [],
                    "source_span_start": item.source_span_start,
                    "source_span_end": item.source_span_end,
                    "notes": item.notes,
                    "materialized_outline_id": item_map.get(item.id).outline_id if item.id in item_map else None,
                    "materialized_chapter_id": item_map.get(item.id).chapter_id if item.id in item_map else None,
                }
                for item in items
            ],
        )

    async def _serialize_audits(
        self,
        db: AsyncSession,
        adaptation_project_id: str,
        *,
        limit: int = 10,
    ) -> list[AdaptationCanonAuditResponse]:
        result = await db.execute(
            select(AdaptationCanonAudit)
            .where(AdaptationCanonAudit.adaptation_project_id == adaptation_project_id)
            .order_by(AdaptationCanonAudit.created_at.desc())
            .limit(limit)
        )
        return [AdaptationCanonAuditResponse.model_validate(row) for row in result.scalars().all()]

    def _extract_json_payload(self, text: str) -> dict[str, Any]:
        parsed = parse_json(text)
        if not isinstance(parsed, dict):
            raise HTTPException(status_code=502, detail="AI 返回格式无效")
        return parsed

    def _build_planning_prompt(
        self,
        *,
        project_title: str,
        brief_text: str,
        batch_size: int,
        batch_number: int,
        retrieved_chunks: list[dict[str, Any]],
        confirmed_batches: list[dict[str, Any]],
        written_chapters: list[dict[str, Any]],
    ) -> str:
        chunks_text = "\n\n".join(
            [
                f"[{chunk['chunk_id']}] 偏移 {chunk['start_offset']}-{chunk['end_offset']}\n{chunk['content']}"
                for chunk in retrieved_chunks
            ]
        )
        confirmed_text = json.dumps(confirmed_batches, ensure_ascii=False, indent=2)
        written_text = json.dumps(written_chapters, ensure_ascii=False, indent=2)
        return f"""
你是小说改编规划助手。请基于原著片段和当前进展，规划“下一批”新章节。

硬性要求：
1. 原著事实优先，绝不改变关键情节和结果。
2. 仅规划下一批，数量不超过 {batch_size} 章。
3. 必须保持时间顺序。
4. 可以合并或拆分原著事件，但不要按原章节原封不动搬运。
5. 风格要求只来自这段自由提示词：
{brief_text}
6. 不要规划整本书，只返回当前下一批。

项目标题：{project_title}
当前是第 {batch_number} 批规划。

已确认批次：
{confirmed_text}

已写正文摘要：
{written_text}

本轮可用原著片段：
{chunks_text}

请只返回 JSON，对象结构如下：
{{
  "batch_summary": "一句话说明本批的推进位置",
  "has_more": true,
  "items": [
    {{
      "title": "章节标题",
      "outline": "适合后续写正文的章节大纲",
      "source_chunk_ids": ["chunk-0001", "chunk-0002"],
      "source_span_start": 0,
      "source_span_end": 1200,
      "notes": "可选说明"
    }}
  ]
}}
""".strip()

    def _build_planning_validation_prompt(
        self,
        *,
        brief_text: str,
        retrieved_chunks: list[dict[str, Any]],
        candidate_items: list[dict[str, Any]],
    ) -> str:
        chunk_text = "\n\n".join(
            [f"[{chunk['chunk_id']}] {chunk['content']}" for chunk in retrieved_chunks]
        )
        candidate_text = json.dumps(candidate_items, ensure_ascii=False, indent=2)
        return f"""
请校验这批改编章节规划是否与原著事实冲突。原著优先，提示词仅作风格要求。

自由提示词：
{brief_text}

原著片段：
{chunk_text}

候选批次：
{candidate_text}

请只返回 JSON：
{{
  "summary": "整体结论",
  "contradiction_results": {{
    "key_plot_outcomes": {{"status": "pass|warn|fail", "reason": "说明"}},
    "character_relationships": {{"status": "pass|warn|fail", "reason": "说明"}},
    "worldbuilding": {{"status": "pass|warn|fail", "reason": "说明"}},
    "organizations": {{"status": "pass|warn|fail", "reason": "说明"}},
    "ending_direction": {{"status": "pass|warn|fail", "reason": "说明"}}
  }}
}}
""".strip()

    def _build_generation_prompt(
        self,
        *,
        project_title: str,
        brief_text: str,
        chapter_title: str,
        chapter_outline: str,
        retrieved_chunks: list[dict[str, Any]],
        prior_chapters: list[dict[str, Any]],
        confirmed_batches: list[dict[str, Any]],
    ) -> str:
        chunk_text = "\n\n".join(
            [f"[{chunk['chunk_id']}] {chunk['content']}" for chunk in retrieved_chunks]
        )
        prior_text = json.dumps(prior_chapters, ensure_ascii=False, indent=2)
        confirmed_text = json.dumps(confirmed_batches, ensure_ascii=False, indent=2)
        return f"""
请写一章改编小说正文。

硬性要求：
1. 原著人物、世界观、组织关系、关键情节结果、结局走向都不能改。
2. 语言要贴近较低阅读年龄，但不要幼稚化剧情逻辑。
3. 按时间顺序写。
4. 减少情爱描写，但不删改事件结果。
5. 只写当前这一章，不要改写之前章节。

项目：{project_title}
自由提示词：
{brief_text}

当前章节标题：{chapter_title}
当前章节大纲：
{chapter_outline}

已确认批次概览：
{confirmed_text}

已有正文进展：
{prior_text}

原著相关片段：
{chunk_text}

请直接输出正文，不要输出 JSON，不要加解释。
""".strip()

    def _build_generation_validation_prompt(
        self,
        *,
        chapter_title: str,
        chapter_content: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> str:
        chunk_text = "\n\n".join(
            [f"[{chunk['chunk_id']}] {chunk['content']}" for chunk in retrieved_chunks]
        )
        return f"""
请校验下面这章改编正文与原著片段是否冲突，只返回 JSON。

章节标题：{chapter_title}

正文：
{chapter_content}

原著片段：
{chunk_text}

JSON 结构：
{{
  "summary": "整体结论",
  "contradiction_results": {{
    "key_plot_outcomes": {{"status": "pass|warn|fail", "reason": "说明"}},
    "character_relationships": {{"status": "pass|warn|fail", "reason": "说明"}},
    "worldbuilding": {{"status": "pass|warn|fail", "reason": "说明"}},
    "organizations": {{"status": "pass|warn|fail", "reason": "说明"}},
    "ending_direction": {{"status": "pass|warn|fail", "reason": "说明"}}
  }}
}}
""".strip()

    def _normalize_contradiction_results(self, payload: dict[str, Any]) -> dict[str, Any]:
        results = payload.get("contradiction_results") or {}
        normalized: dict[str, Any] = {}
        for category in CANON_CATEGORIES:
            entry = results.get(category) or {}
            normalized[category] = {
                "status": entry.get("status", "warn"),
                "reason": entry.get("reason", "未返回明确说明"),
            }
        return normalized

    async def create_project(
        self,
        *,
        user_id: str,
        db: AsyncSession,
        file: UploadFile,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> AdaptationProjectCreateResponse:
        content = await file.read()
        text = content.decode("utf-8", errors="ignore").strip()
        if not text:
            raise HTTPException(status_code=400, detail="原著内容不能为空")

        chunks = self._chunk_source_text(text)
        if not chunks:
            raise HTTPException(status_code=400, detail="原著内容无法切分")

        project = Project(
            user_id=user_id,
            title=(title or self._guess_title(file.filename or "原著改编", text))[:200],
            description=description,
            status="planning",
            wizard_status="completed",
            wizard_step=4,
            outline_mode="one-to-many",
        )
        db.add(project)
        await db.flush()

        adaptation_project = AdaptationProject(
            project_id=project.id,
            user_id=user_id,
            workflow_status="source_uploaded",
            source_corpus_status="ready",
        )
        db.add(adaptation_project)
        await db.flush()

        corpus = AdaptationSourceCorpus(
            adaptation_project_id=adaptation_project.id,
            filename=file.filename or "source.txt",
            content_type=file.content_type,
            file_size=len(content),
            total_characters=len(text),
            total_chunks=len(chunks),
            full_text=text,
            chunk_manifest=chunks,
        )
        db.add(corpus)
        await db.commit()

        return AdaptationProjectCreateResponse(
            adaptation_project_id=adaptation_project.id,
            project_id=project.id,
            title=project.title,
            workflow_status=adaptation_project.workflow_status,
            source_filename=corpus.filename,
            total_characters=corpus.total_characters,
            total_chunks=corpus.total_chunks,
        )

    async def list_projects(self, *, user_id: str, db: AsyncSession) -> list[AdaptationProjectListItem]:
        result = await db.execute(
            select(AdaptationProject, Project, AdaptationSourceCorpus)
            .join(Project, Project.id == AdaptationProject.project_id)
            .join(AdaptationSourceCorpus, AdaptationSourceCorpus.adaptation_project_id == AdaptationProject.id)
            .where(AdaptationProject.user_id == user_id)
            .order_by(AdaptationProject.updated_at.desc())
        )
        rows = result.all()
        items: list[AdaptationProjectListItem] = []
        for adaptation_project, project, corpus in rows:
            brief = await self._get_active_brief(db, adaptation_project.id)
            latest_batch_result = await db.execute(
                select(func.max(AdaptationPlanningBatch.batch_number)).where(
                    AdaptationPlanningBatch.adaptation_project_id == adaptation_project.id
                )
            )
            confirmed_count_result = await db.execute(
                select(func.count(AdaptationPlanningBatch.id)).where(
                    AdaptationPlanningBatch.adaptation_project_id == adaptation_project.id,
                    AdaptationPlanningBatch.status == "confirmed",
                )
            )
            latest_batch_number = latest_batch_result.scalar()
            confirmed_count = confirmed_count_result.scalar()
            items.append(
                AdaptationProjectListItem(
                    adaptation_project_id=adaptation_project.id,
                    project_id=project.id,
                    title=project.title,
                    workflow_status=adaptation_project.workflow_status,
                    source_filename=corpus.filename,
                    brief_version=brief.version if brief else None,
                    latest_batch_number=latest_batch_number or 0,
                    confirmed_batch_count=confirmed_count or 0,
                    created_at=adaptation_project.created_at,
                    updated_at=adaptation_project.updated_at,
                )
            )
        return items

    async def get_project_detail(self, *, adaptation_project_id: str, user_id: str, db: AsyncSession) -> AdaptationProjectDetailResponse:
        adaptation_project, project = await self._get_adaptation_project(db, adaptation_project_id, user_id)
        corpus = await self._get_source_corpus(db, adaptation_project.id)
        brief = await self._get_active_brief(db, adaptation_project.id)

        draft_batch = None
        if adaptation_project.active_batch_id:
            draft_result = await db.execute(
                select(AdaptationPlanningBatch).where(
                    AdaptationPlanningBatch.id == adaptation_project.active_batch_id,
                    AdaptationPlanningBatch.adaptation_project_id == adaptation_project.id,
                )
            )
            draft = draft_result.scalar_one_or_none()
            if draft:
                draft_batch = await self._serialize_batch(db, draft)

        confirmed_result = await db.execute(
            select(AdaptationPlanningBatch)
            .where(
                AdaptationPlanningBatch.adaptation_project_id == adaptation_project.id,
                AdaptationPlanningBatch.status == "confirmed",
            )
            .order_by(AdaptationPlanningBatch.batch_number.asc())
        )
        confirmed_batches = [await self._serialize_batch(db, batch) for batch in confirmed_result.scalars().all()]
        recent_audits = await self._serialize_audits(db, adaptation_project.id)

        return AdaptationProjectDetailResponse(
            adaptation_project_id=adaptation_project.id,
            project_id=project.id,
            title=project.title,
            description=project.description,
            workflow_status=adaptation_project.workflow_status,
            source_filename=corpus.filename,
            total_characters=corpus.total_characters,
            total_chunks=corpus.total_chunks,
            active_brief_text=brief.brief_text if brief else None,
            active_brief_version=brief.version if brief else None,
            example_template=brief.example_template if brief else None,
            draft_batch=draft_batch,
            confirmed_batches=confirmed_batches,
            recent_audits=recent_audits,
            can_edit_brief=adaptation_project.workflow_status not in {"batch_planning", "batch_generating"},
            can_plan_next_batch=adaptation_project.active_batch_id is None,
            created_at=adaptation_project.created_at,
            updated_at=adaptation_project.updated_at,
        )

    async def save_brief(
        self,
        *,
        adaptation_project_id: str,
        user_id: str,
        db: AsyncSession,
        brief_text: str,
        example_template: Optional[str],
    ) -> AdaptationBriefSaveResponse:
        adaptation_project, _ = await self._get_adaptation_project(db, adaptation_project_id, user_id)
        if adaptation_project.workflow_status in {"batch_planning", "batch_generating"}:
            raise HTTPException(status_code=409, detail="当前有运行中的规划或正文生成任务，暂时不能修改提示词")

        current_brief = await self._get_active_brief(db, adaptation_project.id)
        next_version = (current_brief.version if current_brief else 0) + 1
        if current_brief:
            current_brief.is_active = False

        brief = AdaptationBrief(
            adaptation_project_id=adaptation_project.id,
            version=next_version,
            brief_text=brief_text.strip(),
            example_template=example_template,
            is_active=True,
        )
        db.add(brief)
        adaptation_project.workflow_status = "brief_saved"
        await db.commit()
        return AdaptationBriefSaveResponse(
            adaptation_project_id=adaptation_project.id,
            version=brief.version,
            brief_text=brief.brief_text,
            example_template=brief.example_template,
            workflow_status=adaptation_project.workflow_status,
        )

    def _build_confirmed_batch_refs(self, batches: list[AdaptationPlanningBatch]) -> list[dict[str, Any]]:
        return [{"batch_id": batch.id, "batch_number": batch.batch_number} for batch in batches]

    async def _load_confirmed_batches(self, db: AsyncSession, adaptation_project_id: str) -> list[AdaptationPlanningBatch]:
        result = await db.execute(
            select(AdaptationPlanningBatch)
            .where(
                AdaptationPlanningBatch.adaptation_project_id == adaptation_project_id,
                AdaptationPlanningBatch.status == "confirmed",
            )
            .order_by(AdaptationPlanningBatch.batch_number.asc())
        )
        return list(result.scalars().all())

    async def _load_written_chapters(self, db: AsyncSession, project_id: str) -> list[Chapter]:
        result = await db.execute(
            select(Chapter)
            .where(Chapter.project_id == project_id)
            .order_by(Chapter.chapter_number.asc())
        )
        return list(result.scalars().all())

    def _select_chunks_for_next_batch(
        self,
        manifest: list[dict[str, Any]],
        confirmed_chunk_ids: list[str],
        batch_size: int,
    ) -> list[dict[str, Any]]:
        if not manifest:
            return []
        lookup = {chunk["chunk_id"]: index for index, chunk in enumerate(manifest)}
        if confirmed_chunk_ids:
            max_index = max((lookup.get(chunk_id, -1) for chunk_id in confirmed_chunk_ids), default=-1)
            start_index = min(max_index + 1, max(len(manifest) - 1, 0))
        else:
            start_index = 0
        desired = min(len(manifest), max(batch_size * 3, batch_size + 2))
        selected = manifest[start_index:start_index + desired]
        if not selected:
            selected = manifest[-desired:]
        return selected

    async def plan_next_batch(
        self,
        *,
        adaptation_project_id: str,
        user_id: str,
        db: AsyncSession,
        batch_size: int,
        ai_service: AIService,
    ) -> AdaptationPlanningBatchResponse:
        adaptation_project, project = await self._get_adaptation_project(db, adaptation_project_id, user_id)
        brief = await self._get_active_brief(db, adaptation_project.id)
        if not brief:
            raise HTTPException(status_code=400, detail="请先保存自由提示词")
        if adaptation_project.active_batch_id:
            raise HTTPException(status_code=409, detail="当前还有未确认的批次，请先确认后再规划下一批")

        corpus = await self._get_source_corpus(db, adaptation_project.id)
        confirmed_batches = await self._load_confirmed_batches(db, adaptation_project.id)
        confirmed_items: list[AdaptationBatchItem] = []
        for batch in confirmed_batches:
            confirmed_items.extend(await self._get_batch_items(db, batch.id))
        confirmed_chunk_ids = [chunk_id for item in confirmed_items for chunk_id in (item.source_chunk_ids or [])]
        retrieved_chunks = self._select_chunks_for_next_batch(corpus.chunk_manifest or [], confirmed_chunk_ids, batch_size)

        written_chapters = await self._load_written_chapters(db, project.id)
        authored_progress = [
            {
                "chapter_id": chapter.id,
                "chapter_number": chapter.chapter_number,
                "title": chapter.title,
                "summary": chapter.summary,
                "word_count": chapter.word_count,
                "has_content": bool((chapter.content or "").strip()),
            }
            for chapter in written_chapters
        ]

        confirmed_payload = [
            {
                "batch_number": batch.batch_number,
                "summary": batch.batch_summary,
                "items": [
                    {
                        "title": item.proposed_title,
                        "outline": item.proposed_outline,
                        "source_chunk_ids": item.source_chunk_ids,
                    }
                    for item in await self._get_batch_items(db, batch.id)
                ],
            }
            for batch in confirmed_batches
        ]

        adaptation_project.workflow_status = "batch_planning"
        await db.flush()

        next_batch_number = (confirmed_batches[-1].batch_number if confirmed_batches else 0) + 1
        prompt = self._build_planning_prompt(
            project_title=project.title,
            brief_text=brief.brief_text,
            batch_size=batch_size,
            batch_number=next_batch_number,
            retrieved_chunks=retrieved_chunks,
            confirmed_batches=confirmed_payload,
            written_chapters=authored_progress,
        )
        response = await ai_service.generate_text(prompt=prompt, auto_mcp=False, temperature=0.3, max_tokens=5000)
        payload = self._extract_json_payload(response.get("content", ""))
        raw_items = payload.get("items") or []
        if not isinstance(raw_items, list) or not raw_items:
            raise HTTPException(status_code=502, detail="AI 未返回可用的章节规划")

        raw_items = raw_items[:batch_size]

        validation_prompt = self._build_planning_validation_prompt(
            brief_text=brief.brief_text,
            retrieved_chunks=retrieved_chunks,
            candidate_items=raw_items,
        )
        validation_response = await ai_service.generate_text(prompt=validation_prompt, auto_mcp=False, temperature=0.1, max_tokens=1800)
        validation_payload = self._extract_json_payload(validation_response.get("content", ""))

        batch = AdaptationPlanningBatch(
            adaptation_project_id=adaptation_project.id,
            batch_number=next_batch_number,
            requested_batch_size=batch_size,
            brief_version=brief.version,
            status="draft",
            batch_summary=payload.get("batch_summary"),
            retrieval_summary={
                "requested_batch_size": batch_size,
                "retrieved_chunk_ids": [chunk["chunk_id"] for chunk in retrieved_chunks],
                "retrieved_chunk_count": len(retrieved_chunks),
                "confirmed_batch_refs": self._build_confirmed_batch_refs(confirmed_batches),
                "written_chapter_count": len(written_chapters),
            },
        )
        db.add(batch)
        await db.flush()

        for index, item in enumerate(raw_items, start=1):
            batch_item = AdaptationBatchItem(
                batch_id=batch.id,
                item_index=index,
                proposed_title=(item.get("title") or f"第{index}章").strip()[:255],
                proposed_outline=(item.get("outline") or "").strip(),
                source_chunk_ids=item.get("source_chunk_ids") or [chunk["chunk_id"] for chunk in retrieved_chunks[:2]],
                source_span_start=item.get("source_span_start"),
                source_span_end=item.get("source_span_end"),
                notes=item.get("notes"),
            )
            db.add(batch_item)

        audit = AdaptationCanonAudit(
            adaptation_project_id=adaptation_project.id,
            batch_id=batch.id,
            audit_type="planning",
            brief_version=brief.version,
            retrieved_chunk_ids=[chunk["chunk_id"] for chunk in retrieved_chunks],
            provenance=[
                {
                    "chunk_id": chunk["chunk_id"],
                    "start_offset": chunk["start_offset"],
                    "end_offset": chunk["end_offset"],
                }
                for chunk in retrieved_chunks
            ],
            confirmed_batch_refs=self._build_confirmed_batch_refs(confirmed_batches),
            contradiction_results=self._normalize_contradiction_results(validation_payload),
            summary=validation_payload.get("summary") or payload.get("batch_summary"),
            raw_payload={
                "planning_context": {
                    "brief_version": brief.version,
                    "confirmed_batches": confirmed_payload,
                    "written_chapters": authored_progress,
                },
                "planning_result": payload,
                "validation_result": validation_payload,
            },
        )
        db.add(audit)

        adaptation_project.active_batch_id = batch.id
        adaptation_project.workflow_status = "batch_draft_ready"
        await db.commit()
        await db.refresh(batch)
        return await self._serialize_batch(db, batch)

    async def confirm_batch(
        self,
        *,
        adaptation_project_id: str,
        batch_id: str,
        user_id: str,
        db: AsyncSession,
    ) -> AdaptationBatchConfirmResponse:
        adaptation_project, project = await self._get_adaptation_project(db, adaptation_project_id, user_id)
        result = await db.execute(
            select(AdaptationPlanningBatch).where(
                AdaptationPlanningBatch.id == batch_id,
                AdaptationPlanningBatch.adaptation_project_id == adaptation_project.id,
            )
        )
        batch = result.scalar_one_or_none()
        if not batch:
            raise HTTPException(status_code=404, detail="批次不存在")
        if batch.status != "draft":
            raise HTTPException(status_code=400, detail="只有草稿批次可以确认")

        items = await self._get_batch_items(db, batch.id)
        outline_max = await db.execute(select(func.max(Outline.order_index)).where(Outline.project_id == project.id))
        chapter_max = await db.execute(select(func.max(Chapter.chapter_number)).where(Chapter.project_id == project.id))
        next_outline_index = (outline_max.scalar() or 0) + 1
        next_chapter_number = (chapter_max.scalar() or 0) + 1

        for item in items:
            outline = Outline(
                project_id=project.id,
                title=item.proposed_title,
                content=item.proposed_outline,
                order_index=next_outline_index,
                structure=json.dumps(
                    {
                        "source_chunk_ids": item.source_chunk_ids or [],
                        "source_span_start": item.source_span_start,
                        "source_span_end": item.source_span_end,
                        "adaptation_batch_id": batch.id,
                        "adaptation_batch_item_id": item.id,
                    },
                    ensure_ascii=False,
                ),
            )
            db.add(outline)
            await db.flush()

            chapter = Chapter(
                project_id=project.id,
                chapter_number=next_chapter_number,
                title=item.proposed_title,
                summary=item.proposed_outline,
                content="",
                word_count=0,
                status="draft",
                outline_id=outline.id,
                sub_index=1,
            )
            db.add(chapter)
            await db.flush()

            db.add(
                AdaptationMaterializationMap(
                    adaptation_project_id=adaptation_project.id,
                    batch_id=batch.id,
                    batch_item_id=item.id,
                    outline_id=outline.id,
                    chapter_id=chapter.id,
                )
            )
            next_outline_index += 1
            next_chapter_number += 1

        batch.status = "confirmed"
        batch.confirmed_at = func.now()
        adaptation_project.active_batch_id = None
        adaptation_project.last_confirmed_batch_id = batch.id
        adaptation_project.workflow_status = "batch_confirmed"
        await db.commit()

        return AdaptationBatchConfirmResponse(
            success=True,
            adaptation_project_id=adaptation_project.id,
            batch_id=batch.id,
            materialized_count=len(items),
            project_id=project.id,
        )

    async def generate_chapter(
        self,
        *,
        adaptation_project_id: str,
        batch_item_id: str,
        chapter_id: str,
        regenerate: bool,
        user_id: str,
        db: AsyncSession,
        ai_service: AIService,
    ) -> AdaptationChapterGenerateResponse:
        adaptation_project, project = await self._get_adaptation_project(db, adaptation_project_id, user_id)
        if adaptation_project.workflow_status == "batch_planning":
            raise HTTPException(status_code=409, detail="当前正在规划批次，请稍后")

        item_result = await db.execute(select(AdaptationBatchItem).where(AdaptationBatchItem.id == batch_item_id))
        batch_item = item_result.scalar_one_or_none()
        if not batch_item:
            raise HTTPException(status_code=404, detail="批次章节项不存在")

        batch_result = await db.execute(select(AdaptationPlanningBatch).where(AdaptationPlanningBatch.id == batch_item.batch_id))
        batch = batch_result.scalar_one_or_none()
        if not batch or batch.adaptation_project_id != adaptation_project.id:
            raise HTTPException(status_code=404, detail="批次不存在")
        if batch.status != "confirmed":
            raise HTTPException(status_code=400, detail="请先确认当前批次，再生成正文")

        chapter_result = await db.execute(
            select(Chapter).where(Chapter.id == chapter_id, Chapter.project_id == project.id)
        )
        chapter = chapter_result.scalar_one_or_none()
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")
        if chapter.content and not regenerate:
            raise HTTPException(status_code=409, detail="章节已有正文，如需重写请显式选择重新生成")

        brief = await self._get_active_brief(db, adaptation_project.id)
        if not brief:
            raise HTTPException(status_code=400, detail="缺少自由提示词")
        corpus = await self._get_source_corpus(db, adaptation_project.id)

        manifest = corpus.chunk_manifest or []
        chunk_lookup = {chunk["chunk_id"]: chunk for chunk in manifest}
        retrieved_chunks = [chunk_lookup[chunk_id] for chunk_id in (batch_item.source_chunk_ids or []) if chunk_id in chunk_lookup]
        if not retrieved_chunks:
            retrieved_chunks = manifest[:3]

        confirmed_batches = await self._load_confirmed_batches(db, adaptation_project.id)
        confirmed_refs = self._build_confirmed_batch_refs(confirmed_batches)
        prior_chapters = await self._load_written_chapters(db, project.id)
        prior_payload = [
            {
                "chapter_number": item.chapter_number,
                "title": item.title,
                "summary": item.summary,
                "content_excerpt": (item.content or "")[:1200],
            }
            for item in prior_chapters
            if item.id != chapter.id and (item.content or "").strip()
        ]

        adaptation_project.workflow_status = "batch_generating"
        await db.flush()

        prompt = self._build_generation_prompt(
            project_title=project.title,
            brief_text=brief.brief_text,
            chapter_title=chapter.title,
            chapter_outline=chapter.summary or batch_item.proposed_outline,
            retrieved_chunks=retrieved_chunks,
            prior_chapters=prior_payload,
            confirmed_batches=confirmed_refs,
        )
        response = await ai_service.generate_text(prompt=prompt, auto_mcp=False, temperature=0.5, max_tokens=7000)
        content = (response.get("content", "") or "").strip()
        if not content:
            raise HTTPException(status_code=502, detail="AI 未返回正文")

        validation_prompt = self._build_generation_validation_prompt(
            chapter_title=chapter.title,
            chapter_content=content,
            retrieved_chunks=retrieved_chunks,
        )
        validation_response = await ai_service.generate_text(prompt=validation_prompt, auto_mcp=False, temperature=0.1, max_tokens=1800)
        validation_payload = self._extract_json_payload(validation_response.get("content", ""))

        chapter.content = content
        chapter.word_count = len(re.sub(r"\s+", "", content))
        chapter.status = "draft"

        audit = AdaptationCanonAudit(
            adaptation_project_id=adaptation_project.id,
            batch_id=batch.id,
            batch_item_id=batch_item.id,
            target_chapter_id=chapter.id,
            audit_type="generation",
            brief_version=brief.version,
            retrieved_chunk_ids=[chunk["chunk_id"] for chunk in retrieved_chunks],
            provenance=[
                {
                    "chunk_id": chunk["chunk_id"],
                    "start_offset": chunk["start_offset"],
                    "end_offset": chunk["end_offset"],
                }
                for chunk in retrieved_chunks
            ],
            confirmed_batch_refs=confirmed_refs,
            contradiction_results=self._normalize_contradiction_results(validation_payload),
            summary=validation_payload.get("summary"),
            raw_payload={
                "generation_context": {
                    "brief_version": brief.version,
                    "prior_chapters": prior_payload,
                    "chapter_title": chapter.title,
                },
                "validation_result": validation_payload,
            },
        )
        db.add(audit)
        adaptation_project.workflow_status = "batch_written"
        await db.commit()
        await db.refresh(chapter)
        await db.refresh(audit)

        return AdaptationChapterGenerateResponse(
            success=True,
            project_id=project.id,
            chapter_id=chapter.id,
            title=chapter.title,
            word_count=chapter.word_count or 0,
            audit_id=audit.id,
        )


original_novel_adaptation_service = OriginalNovelAdaptationService()
