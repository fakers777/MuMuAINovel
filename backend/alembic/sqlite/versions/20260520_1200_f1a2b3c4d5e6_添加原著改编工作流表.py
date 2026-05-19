"""添加原著改编工作流表

Revision ID: f1a2b3c4d5e6
Revises: c6d7e8f9a0b1
Create Date: 2026-05-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = set(inspector.get_table_names())

    if "adaptation_projects" not in table_names:
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
    else:
        existing_columns = {column["name"] for column in inspector.get_columns("adaptation_projects")}
        if "user_id" not in existing_columns:
            op.add_column("adaptation_projects", sa.Column("user_id", sa.String(length=100), nullable=True))
            op.execute(
                """
                UPDATE adaptation_projects
                SET user_id = COALESCE(
                    (SELECT user_id FROM projects WHERE projects.id = adaptation_projects.project_id),
                    'legacy-adaptation-user'
                )
                WHERE user_id IS NULL
                """
            )
        if "source_corpus_status" not in existing_columns:
            op.add_column(
                "adaptation_projects",
                sa.Column("source_corpus_status", sa.String(length=32), nullable=True),
            )
            op.execute(
                """
                UPDATE adaptation_projects
                SET source_corpus_status = CASE
                    WHEN source_filename IS NOT NULL AND trim(source_filename) <> '' THEN 'completed'
                    ELSE 'pending'
                END
                WHERE source_corpus_status IS NULL
                """
            )
        if "active_batch_id" not in existing_columns:
            op.add_column("adaptation_projects", sa.Column("active_batch_id", sa.String(length=36), nullable=True))
        if "last_confirmed_batch_id" not in existing_columns:
            op.add_column("adaptation_projects", sa.Column("last_confirmed_batch_id", sa.String(length=36), nullable=True))
        if "created_at" not in existing_columns:
            op.add_column(
                "adaptation_projects",
                sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            )
        if "updated_at" not in existing_columns:
            op.add_column(
                "adaptation_projects",
                sa.Column("updated_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
            )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_adaptation_projects_project_id "
        "ON adaptation_projects (project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_projects_user_id "
        "ON adaptation_projects (user_id)"
    )

    if "adaptation_source_corpora" not in table_names:
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
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_adaptation_source_corpora_adaptation_project_id "
        "ON adaptation_source_corpora (adaptation_project_id)"
    )

    if "adaptation_briefs" not in table_names:
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_briefs_adaptation_project_id "
        "ON adaptation_briefs (adaptation_project_id)"
    )

    if "adaptation_planning_batches" not in table_names:
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_planning_batches_adaptation_project_id "
        "ON adaptation_planning_batches (adaptation_project_id)"
    )

    if "adaptation_batch_items" not in table_names:
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_batch_items_batch_id "
        "ON adaptation_batch_items (batch_id)"
    )

    if "adaptation_canon_audits" not in table_names:
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_canon_audits_adaptation_project_id "
        "ON adaptation_canon_audits (adaptation_project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_canon_audits_batch_id "
        "ON adaptation_canon_audits (batch_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_canon_audits_batch_item_id "
        "ON adaptation_canon_audits (batch_item_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_canon_audits_target_chapter_id "
        "ON adaptation_canon_audits (target_chapter_id)"
    )

    if "adaptation_materialization_maps" not in table_names:
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
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_materialization_maps_adaptation_project_id "
        "ON adaptation_materialization_maps (adaptation_project_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_materialization_maps_batch_id "
        "ON adaptation_materialization_maps (batch_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_adaptation_materialization_maps_batch_item_id "
        "ON adaptation_materialization_maps (batch_item_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_materialization_maps_outline_id "
        "ON adaptation_materialization_maps (outline_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_adaptation_materialization_maps_chapter_id "
        "ON adaptation_materialization_maps (chapter_id)"
    )


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
