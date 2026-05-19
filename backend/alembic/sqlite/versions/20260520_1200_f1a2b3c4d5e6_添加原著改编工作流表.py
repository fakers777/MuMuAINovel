"""添加原著改编工作流表

Revision ID: f1a2b3c4d5e6
Revises: 3a08fc61773f
Create Date: 2026-05-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "3a08fc61773f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "adaptation_projects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("workflow_status", sa.String(length=32), nullable=False),
        sa.Column("source_corpus_status", sa.String(length=32), nullable=False),
        sa.Column("active_batch_id", sa.String(length=36), nullable=True),
        sa.Column("last_confirmed_batch_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index(op.f("ix_adaptation_projects_project_id"), "adaptation_projects", ["project_id"], unique=True)
    op.create_index(op.f("ix_adaptation_projects_user_id"), "adaptation_projects", ["user_id"], unique=False)

    op.create_table(
        "adaptation_source_corpora",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("adaptation_project_id", sa.String(length=36), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("total_characters", sa.Integer(), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("chunk_manifest", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["adaptation_project_id"], ["adaptation_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adaptation_project_id"),
    )
    op.create_index(op.f("ix_adaptation_source_corpora_adaptation_project_id"), "adaptation_source_corpora", ["adaptation_project_id"], unique=True)

    op.create_table(
        "adaptation_briefs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("adaptation_project_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("brief_text", sa.Text(), nullable=False),
        sa.Column("example_template", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["adaptation_project_id"], ["adaptation_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adaptation_project_id", "version", name="uq_adaptation_brief_project_version"),
    )
    op.create_index(op.f("ix_adaptation_briefs_adaptation_project_id"), "adaptation_briefs", ["adaptation_project_id"], unique=False)

    op.create_table(
        "adaptation_planning_batches",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("adaptation_project_id", sa.String(length=36), nullable=False),
        sa.Column("batch_number", sa.Integer(), nullable=False),
        sa.Column("requested_batch_size", sa.Integer(), nullable=False),
        sa.Column("brief_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("batch_summary", sa.Text(), nullable=True),
        sa.Column("retrieval_summary", sa.JSON(), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["adaptation_project_id"], ["adaptation_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("adaptation_project_id", "batch_number", name="uq_adaptation_batch_project_number"),
    )
    op.create_index(op.f("ix_adaptation_planning_batches_adaptation_project_id"), "adaptation_planning_batches", ["adaptation_project_id"], unique=False)

    op.create_table(
        "adaptation_batch_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column("proposed_title", sa.String(length=255), nullable=False),
        sa.Column("proposed_outline", sa.Text(), nullable=False),
        sa.Column("source_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("source_span_start", sa.Integer(), nullable=True),
        sa.Column("source_span_end", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["adaptation_planning_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "item_index", name="uq_adaptation_batch_item_order"),
    )
    op.create_index(op.f("ix_adaptation_batch_items_batch_id"), "adaptation_batch_items", ["batch_id"], unique=False)

    op.create_table(
        "adaptation_canon_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("adaptation_project_id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=True),
        sa.Column("batch_item_id", sa.String(length=36), nullable=True),
        sa.Column("target_chapter_id", sa.String(length=36), nullable=True),
        sa.Column("audit_type", sa.String(length=24), nullable=False),
        sa.Column("brief_version", sa.Integer(), nullable=True),
        sa.Column("retrieved_chunk_ids", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("confirmed_batch_refs", sa.JSON(), nullable=False),
        sa.Column("contradiction_results", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["adaptation_project_id"], ["adaptation_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["adaptation_planning_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_item_id"], ["adaptation_batch_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_adaptation_canon_audits_adaptation_project_id"), "adaptation_canon_audits", ["adaptation_project_id"], unique=False)
    op.create_index(op.f("ix_adaptation_canon_audits_batch_id"), "adaptation_canon_audits", ["batch_id"], unique=False)
    op.create_index(op.f("ix_adaptation_canon_audits_batch_item_id"), "adaptation_canon_audits", ["batch_item_id"], unique=False)
    op.create_index(op.f("ix_adaptation_canon_audits_target_chapter_id"), "adaptation_canon_audits", ["target_chapter_id"], unique=False)

    op.create_table(
        "adaptation_materialization_maps",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("adaptation_project_id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("batch_item_id", sa.String(length=36), nullable=False),
        sa.Column("outline_id", sa.String(length=36), nullable=False),
        sa.Column("chapter_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["adaptation_project_id"], ["adaptation_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["adaptation_planning_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_item_id"], ["adaptation_batch_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["outline_id"], ["outlines.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_item_id"),
    )
    op.create_index(op.f("ix_adaptation_materialization_maps_adaptation_project_id"), "adaptation_materialization_maps", ["adaptation_project_id"], unique=False)
    op.create_index(op.f("ix_adaptation_materialization_maps_batch_id"), "adaptation_materialization_maps", ["batch_id"], unique=False)
    op.create_index(op.f("ix_adaptation_materialization_maps_batch_item_id"), "adaptation_materialization_maps", ["batch_item_id"], unique=True)
    op.create_index(op.f("ix_adaptation_materialization_maps_outline_id"), "adaptation_materialization_maps", ["outline_id"], unique=False)
    op.create_index(op.f("ix_adaptation_materialization_maps_chapter_id"), "adaptation_materialization_maps", ["chapter_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_adaptation_materialization_maps_chapter_id"), table_name="adaptation_materialization_maps")
    op.drop_index(op.f("ix_adaptation_materialization_maps_outline_id"), table_name="adaptation_materialization_maps")
    op.drop_index(op.f("ix_adaptation_materialization_maps_batch_item_id"), table_name="adaptation_materialization_maps")
    op.drop_index(op.f("ix_adaptation_materialization_maps_batch_id"), table_name="adaptation_materialization_maps")
    op.drop_index(op.f("ix_adaptation_materialization_maps_adaptation_project_id"), table_name="adaptation_materialization_maps")
    op.drop_table("adaptation_materialization_maps")
    op.drop_index(op.f("ix_adaptation_canon_audits_target_chapter_id"), table_name="adaptation_canon_audits")
    op.drop_index(op.f("ix_adaptation_canon_audits_batch_item_id"), table_name="adaptation_canon_audits")
    op.drop_index(op.f("ix_adaptation_canon_audits_batch_id"), table_name="adaptation_canon_audits")
    op.drop_index(op.f("ix_adaptation_canon_audits_adaptation_project_id"), table_name="adaptation_canon_audits")
    op.drop_table("adaptation_canon_audits")
    op.drop_index(op.f("ix_adaptation_batch_items_batch_id"), table_name="adaptation_batch_items")
    op.drop_table("adaptation_batch_items")
    op.drop_index(op.f("ix_adaptation_planning_batches_adaptation_project_id"), table_name="adaptation_planning_batches")
    op.drop_table("adaptation_planning_batches")
    op.drop_index(op.f("ix_adaptation_briefs_adaptation_project_id"), table_name="adaptation_briefs")
    op.drop_table("adaptation_briefs")
    op.drop_index(op.f("ix_adaptation_source_corpora_adaptation_project_id"), table_name="adaptation_source_corpora")
    op.drop_table("adaptation_source_corpora")
    op.drop_index(op.f("ix_adaptation_projects_user_id"), table_name="adaptation_projects")
    op.drop_index(op.f("ix_adaptation_projects_project_id"), table_name="adaptation_projects")
    op.drop_table("adaptation_projects")
