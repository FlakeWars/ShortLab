"""create core domain schema

Revision ID: 9f3a2c7d8b1e
Revises: 
Create Date: 2026-02-02 13:00:00

Purpose:
- introduce the core domain tables defined in .ai/db-plan.md
- add required constraints and indexes for query performance
- enable row level security (rls) and define per-role policies

Touched tables / objects:
- user_account, dsl_version, design_system_version, idea_batch, idea_candidate, idea,
  idea_similarity, idea_embedding, animation, render, artifact, qc_checklist_version, qc_checklist_item,
  qc_decision, publish_record, metrics_pull_run, metrics_daily, tag, animation_tag,
  tag_event, pipeline_run, job, job_stage_run, platform_config, audit_event
- indexes as listed in the db plan (including gin indexes for jsonb payloads)
- required extensions: pgcrypto, citext (pg_trgm is optional)

Operational notes:
- creating many tables and indexes will take locks; run during a quiet window
- rls is enabled for every new table; policies are explicit per role and operation
- for owner-only policies, this migration assumes the app sets per-connection settings
  (e.g. set_config('app.user_id', ...) and optionally set_config('app.is_system', ...))
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9f3a2c7d8b1e"
down_revision = None
branch_labels = None
depends_on = None


APP_USER_ID = "nullif(current_setting('app.user_id', true), '')::uuid"
APP_IS_SYSTEM = "current_setting('app.is_system', true) = 'true'"


def _enable_rls(table_name: str, force: bool = False, force_reason: str | None = None) -> None:
    op.execute(
        f"""
-- enable rls for table {table_name}
alter table public.{table_name} enable row level security;
"""
    )
    if force:
        comment = "" if not force_reason else f" -- {force_reason}"
        op.execute(
            f"""
-- force rls for table {table_name}{comment}
alter table public.{table_name} force row level security;
"""
        )


def _create_policy(
    table_name: str,
    role_name: str,
    operation: str,
    using_expr: str | None,
    check_expr: str | None,
    comment: str,
) -> None:
    policy_name = f"rls_{table_name}_{operation}_{role_name}"
    if operation == "select":
        op.execute(
            f"""
-- {comment}
create policy {policy_name} on public.{table_name}
  for select
  to {role_name}
  using ({using_expr});
"""
        )
        return
    if operation == "delete":
        op.execute(
            f"""
-- {comment}
create policy {policy_name} on public.{table_name}
  for delete
  to {role_name}
  using ({using_expr});
"""
        )
        return
    if operation == "insert":
        op.execute(
            f"""
-- {comment}
create policy {policy_name} on public.{table_name}
  for insert
  to {role_name}
  with check ({check_expr});
"""
        )
        return
    if operation == "update":
        op.execute(
            f"""
-- {comment}
create policy {policy_name} on public.{table_name}
  for update
  to {role_name}
  using ({using_expr})
  with check ({check_expr});
"""
        )
        return
    raise ValueError(f"unsupported operation for rls policy: {operation}")


def _create_basic_policies(table_name: str) -> None:
    # anon: deny all access by default
    _create_policy(
        table_name,
        "anon",
        "select",
        "false",
        None,
        "deny anon read access",
    )
    _create_policy(
        table_name,
        "anon",
        "insert",
        None,
        "false",
        "deny anon insert access",
    )
    _create_policy(
        table_name,
        "anon",
        "update",
        "false",
        "false",
        "deny anon update access",
    )
    _create_policy(
        table_name,
        "anon",
        "delete",
        "false",
        None,
        "deny anon delete access",
    )

    # authenticated: allow full access; application enforces finer-grained rules
    _create_policy(
        table_name,
        "authenticated",
        "select",
        "true",
        None,
        "allow authenticated read access",
    )
    _create_policy(
        table_name,
        "authenticated",
        "insert",
        None,
        "true",
        "allow authenticated insert access",
    )
    _create_policy(
        table_name,
        "authenticated",
        "update",
        "true",
        "true",
        "allow authenticated update access",
    )
    _create_policy(
        table_name,
        "authenticated",
        "delete",
        "true",
        None,
        "allow authenticated delete access",
    )


def upgrade() -> None:
    # extensions required by the schema
    op.execute(
        """
-- required for gen_random_uuid()
create extension if not exists pgcrypto;
-- required for citext email columns
create extension if not exists citext;
"""
    )

    # ensure application roles exist; requires sufficient privileges
    op.execute(
        """
-- precondition: this block requires create role privilege
-- if role creation is managed elsewhere, it is safe to no-op
 do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated;
  end if;
end$$;
"""
    )

    # core tables
    op.create_table(
        "user_account",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_user_account_email"),
    )

    op.create_table(
        "dsl_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("schema_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_dsl_version_version"),
    )

    op.create_table(
        "design_system_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("meta", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version", name="uq_design_system_version_version"),
    )

    op.create_table(
        "idea_batch",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("window_id", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("source in ('schedule', 'manual')", name="ck_idea_batch_source"),
        sa.UniqueConstraint("run_date", "window_id", name="uq_idea_batch_run_window"),
    )

    op.create_table(
        "idea_candidate",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("idea_batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("what_to_expect", sa.Text(), nullable=True),
        sa.Column("preview", sa.Text(), nullable=True),
        sa.Column("generator_source", sa.Text(), nullable=False),
        sa.Column("similarity_status", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'new'")),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("selected_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["idea_batch_id"], ["idea_batch.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selected_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decision_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.CheckConstraint("generator_source in ('ai', 'fallback', 'manual')", name="ck_idea_candidate_generator_source"),
        sa.CheckConstraint("similarity_status in ('ok', 'too_similar', 'unknown')", name="ck_idea_candidate_similarity_status"),
        sa.CheckConstraint("status in ('new', 'later', 'picked')", name="ck_idea_candidate_status"),
    )

    op.create_table(
        "idea",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("idea_candidate_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("what_to_expect", sa.Text(), nullable=True),
        sa.Column("preview", sa.Text(), nullable=True),
        sa.Column("idea_hash", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'unverified'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["idea_candidate_id"], ["idea_candidate.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status in ('unverified', 'feasible', 'blocked_by_gaps', 'ready_for_gate', 'picked', 'compiled')",
            name="ck_idea_status",
        ),
    )

    op.create_table(
        "dsl_gap",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("gap_key", sa.Text(), nullable=False),
        sa.Column("dsl_version", sa.Text(), nullable=False),
        sa.Column("feature", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'new'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gap_key", name="uq_dsl_gap_gap_key"),
        sa.CheckConstraint(
            "status in ('new', 'accepted', 'in_progress', 'implemented', 'rejected')",
            name="ck_dsl_gap_status",
        ),
    )

    op.create_table(
        "idea_gap_link",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dsl_gap_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["idea_id"], ["idea.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dsl_gap_id"], ["dsl_gap.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idea_id", "dsl_gap_id", name="uq_idea_gap_link_idea_gap"),
    )

    op.create_table(
        "idea_similarity",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("idea_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("compared_idea_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Numeric(5, 4), nullable=False),
        sa.Column("embedding_version", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["idea_candidate_id"], ["idea_candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["compared_idea_id"], ["idea.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("idea_candidate_id", "compared_idea_id", name="uq_idea_similarity_pair"),
    )

    op.create_table(
        "idea_embedding",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("idea_candidate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("vector", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["idea_candidate_id"], ["idea_candidate.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["idea_id"], ["idea.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("idea_candidate_id", "version", name="uq_idea_embedding_candidate_version"),
    )

    op.create_table(
        "animation",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("animation_code", sa.Text(), nullable=False),
        sa.Column("idea_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("parent_animation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("pipeline_stage", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("soft_deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("animation_code", name="uq_animation_animation_code"),
        sa.ForeignKeyConstraint(["idea_id"], ["idea.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_animation_id"], ["animation.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status in ('draft', 'queued', 'running', 'review', 'accepted', 'rejected', 'published', 'archived')",
            name="ck_animation_status",
        ),
        sa.CheckConstraint(
            "pipeline_stage in ('idea', 'render', 'qc', 'publish', 'metrics', 'done')",
            name="ck_animation_pipeline_stage",
        ),
    )

    op.create_table(
        "render",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("animation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_render_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("seed", sa.BigInteger(), nullable=False),
        sa.Column("dsl_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("design_system_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("renderer_version", sa.Text(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("fps", sa.Numeric(6, 3), nullable=False),
        sa.Column("params_json", postgresql.JSONB(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["animation_id"], ["animation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_render_id"], ["render.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["dsl_version_id"], ["dsl_version.id"]),
        sa.ForeignKeyConstraint(["design_system_version_id"], ["design_system_version.id"]),
        sa.CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_render_status"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_render_duration_non_negative"),
    )

    op.create_table(
        "artifact",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("render_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.Text(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["render_id"], ["render.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "artifact_type in ('video', 'preview', 'thumbnail', 'dsl', 'metadata', 'other')",
            name="ck_artifact_type",
        ),
    )

    op.create_table(
        "qc_checklist_version",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("version", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", "version", name="uq_qc_checklist_version_name_version"),
    )

    op.create_table(
        "qc_checklist_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("checklist_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_key", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["checklist_version_id"], ["qc_checklist_version.id"], ondelete="CASCADE"),
        sa.CheckConstraint("severity in ('hard', 'soft')", name="ck_qc_checklist_item_severity"),
        sa.UniqueConstraint("checklist_version_id", "item_key", name="uq_qc_checklist_item_key"),
    )

    op.create_table(
        "qc_decision",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("animation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("checklist_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("decision_payload", postgresql.JSONB(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["animation_id"], ["animation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["checklist_version_id"], ["qc_checklist_version.id"]),
        sa.ForeignKeyConstraint(["decided_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.CheckConstraint("result in ('accepted', 'rejected', 'regenerate')", name="ck_qc_decision_result"),
    )

    op.create_table(
        "publish_record",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("render_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("content_id", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["render_id"], ["render.id"], ondelete="CASCADE"),
        sa.CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_publish_record_platform_type"),
        sa.CheckConstraint(
            "status in ('queued', 'uploading', 'published', 'failed', 'manual_confirmed')",
            name="ck_publish_record_status",
        ),
        sa.UniqueConstraint("platform_type", "content_id", name="uq_publish_record_platform_content"),
    )

    op.create_table(
        "metrics_pull_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("platform_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_metrics_pull_run_platform_type"),
        sa.CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_metrics_pull_run_status"),
        sa.CheckConstraint("source in ('api', 'manual')", name="ck_metrics_pull_run_source"),
    )

    op.create_table(
        "metrics_daily",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("platform_type", sa.Text(), nullable=False),
        sa.Column("content_id", sa.Text(), nullable=False),
        sa.Column("publish_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("render_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("likes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("comments", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("shares", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("watch_time_seconds", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("avg_view_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("avg_view_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("extra_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["publish_record_id"], ["publish_record.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["render_id"], ["render.id"], ondelete="SET NULL"),
        sa.CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_metrics_daily_platform_type"),
        sa.UniqueConstraint("platform_type", "content_id", "date", name="uq_metrics_daily_content_date"),
    )

    op.create_table(
        "tag",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tag_type", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tag_name"),
        sa.CheckConstraint("tag_type in ('canonical', 'experimental')", name="ck_tag_type"),
    )

    op.create_table(
        "animation_tag",
        sa.Column("animation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("animation_id", "tag_id"),
        sa.ForeignKeyConstraint(["animation_id"], ["animation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["added_by"], ["user_account.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "tag_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("animation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("changed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["animation_id"], ["animation.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tag.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.CheckConstraint("action in ('added', 'removed', 'edited')", name="ck_tag_event_action"),
        sa.CheckConstraint("source in ('ui', 'system')", name="ck_tag_event_source"),
    )

    op.create_table(
        "pipeline_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("idea_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("window_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["idea_batch_id"], ["idea_batch.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status in ('scheduled', 'running', 'succeeded', 'failed', 'canceled')",
            name="ck_pipeline_run_status",
        ),
        sa.UniqueConstraint("run_date", "window_id", name="uq_pipeline_run_run_window"),
    )

    op.create_table(
        "job",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("job_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("parent_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("error_payload", postgresql.JSONB(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parent_job_id"], ["job.id"], ondelete="SET NULL"),
        sa.CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_job_status"),
    )

    op.create_table(
        "job_stage_run",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("pipeline_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_payload", postgresql.JSONB(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pipeline_run_id"], ["pipeline_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"], ondelete="SET NULL"),
        sa.CheckConstraint("stage in ('generate', 'idea_gate', 'render', 'qc', 'publish', 'metrics')", name="ck_job_stage_run_stage"),
        sa.CheckConstraint("status in ('queued', 'running', 'succeeded', 'failed')", name="ck_job_stage_run_status"),
    )

    op.create_table(
        "platform_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("platform_type", sa.Text(), nullable=False),
        sa.Column("encrypted_payload", sa.LargeBinary(), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["updated_by"], ["user_account.id"], ondelete="SET NULL"),
        sa.CheckConstraint("platform_type in ('youtube', 'tiktok')", name="ck_platform_config_platform_type"),
        sa.UniqueConstraint("platform_type", name="uq_platform_config_platform_type"),
    )

    op.create_table(
        "audit_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user_account.id"], ondelete="SET NULL"),
        sa.CheckConstraint("source in ('ui', 'system', 'worker')", name="ck_audit_event_source"),
    )

    # indexes for performance
    op.create_index("ix_animation_status_created_at", "animation", ["status", "created_at"], unique=False)
    op.create_index("ix_animation_pipeline_stage_updated_at", "animation", ["pipeline_stage", "updated_at"], unique=False)
    op.create_index("ix_render_animation_id_created_at", "render", ["animation_id", "created_at"], unique=False)
    op.create_index("ix_publish_record_platform_published_at", "publish_record", ["platform_type", "published_at"], unique=False)
    op.create_index("ix_metrics_daily_platform_date", "metrics_daily", ["platform_type", "date"], unique=False)
    op.create_index("ix_metrics_daily_render_date", "metrics_daily", ["render_id", "date"], unique=False)
    op.create_index("ix_job_status_updated_at", "job", ["status", "updated_at"], unique=False)
    op.create_index("ix_job_stage_run_pipeline_stage", "job_stage_run", ["pipeline_run_id", "stage"], unique=False)
    op.create_index("ix_idea_status_created_at", "idea", ["status", "created_at"], unique=False)
    op.create_index("ix_dsl_gap_status_updated_at", "dsl_gap", ["status", "updated_at"], unique=False)

    op.create_index(
        "ix_render_params_json_gin",
        "render",
        ["params_json"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_render_metadata_json_gin",
        "render",
        ["metadata_json"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_qc_decision_payload_gin",
        "qc_decision",
        ["decision_payload"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_job_error_payload_gin",
        "job",
        ["error_payload"],
        unique=False,
        postgresql_using="gin",
    )
    op.create_index(
        "ix_audit_event_payload_gin",
        "audit_event",
        ["payload"],
        unique=False,
        postgresql_using="gin",
    )

    op.execute(
        """
-- optional trigram index for tag.name; this requires pg_trgm
-- if pg_trgm is not installed, this block safely does nothing
 do $$
begin
  if exists (select 1 from pg_extension where extname = 'pg_trgm') then
    create index if not exists ix_tag_name_trgm on public.tag using gin (name gin_trgm_ops);
  end if;
end$$;
"""
    )

    # row level security: enable and define policies
    for table_name in [
        "user_account",
        "dsl_version",
        "design_system_version",
        "idea_batch",
        "idea_candidate",
        "idea",
        "dsl_gap",
        "idea_gap_link",
        "idea_similarity",
        "idea_embedding",
        "animation",
        "render",
        "artifact",
        "qc_checklist_version",
        "qc_checklist_item",
        "qc_decision",
        "publish_record",
        "metrics_pull_run",
        "metrics_daily",
        "tag",
        "animation_tag",
        "tag_event",
        "pipeline_run",
        "job",
        "job_stage_run",
        "platform_config",
        "audit_event",
    ]:
        _enable_rls(
            table_name,
            force=table_name in {"platform_config", "audit_event"},
            force_reason=(
                "force rls to protect sensitive records even from table owner"
                if table_name in {"platform_config", "audit_event"}
                else None
            ),
        )

    # default policies for most tables
    for table_name in [
        "dsl_version",
        "design_system_version",
        "idea_batch",
        "idea_candidate",
        "idea",
        "dsl_gap",
        "idea_gap_link",
        "idea_similarity",
        "idea_embedding",
        "animation",
        "render",
        "artifact",
        "qc_checklist_version",
        "qc_checklist_item",
        "qc_decision",
        "publish_record",
        "metrics_pull_run",
        "metrics_daily",
        "tag",
        "animation_tag",
        "tag_event",
        "pipeline_run",
        "job",
        "job_stage_run",
    ]:
        _create_basic_policies(table_name)

    # user_account: owner-only access based on app.user_id
    _create_policy(
        "user_account",
        "anon",
        "select",
        "false",
        None,
        "deny anon read access",
    )
    _create_policy(
        "user_account",
        "anon",
        "insert",
        None,
        "false",
        "deny anon insert access",
    )
    _create_policy(
        "user_account",
        "anon",
        "update",
        "false",
        "false",
        "deny anon update access",
    )
    _create_policy(
        "user_account",
        "anon",
        "delete",
        "false",
        None,
        "deny anon delete access",
    )

    _create_policy(
        "user_account",
        "authenticated",
        "select",
        f"{APP_USER_ID} = id",
        None,
        "allow users to read their own account; assumes app.user_id is set",
    )
    _create_policy(
        "user_account",
        "authenticated",
        "insert",
        None,
        f"{APP_USER_ID} = id",
        "allow users to create their own account; assumes app.user_id matches new id",
    )
    _create_policy(
        "user_account",
        "authenticated",
        "update",
        f"{APP_USER_ID} = id",
        f"{APP_USER_ID} = id",
        "allow users to update their own account; assumes app.user_id is set",
    )
    _create_policy(
        "user_account",
        "authenticated",
        "delete",
        f"{APP_USER_ID} = id",
        None,
        "allow users to delete their own account; assumes app.user_id is set",
    )

    # platform_config: owner-only; force rls to protect secrets
    _create_policy(
        "platform_config",
        "anon",
        "select",
        "false",
        None,
        "deny anon read access",
    )
    _create_policy(
        "platform_config",
        "anon",
        "insert",
        None,
        "false",
        "deny anon insert access",
    )
    _create_policy(
        "platform_config",
        "anon",
        "update",
        "false",
        "false",
        "deny anon update access",
    )
    _create_policy(
        "platform_config",
        "anon",
        "delete",
        "false",
        None,
        "deny anon delete access",
    )

    _create_policy(
        "platform_config",
        "authenticated",
        "select",
        f"{APP_USER_ID} = updated_by",
        None,
        "allow read when app.user_id matches updated_by; assumes per-connection app.user_id",
    )
    _create_policy(
        "platform_config",
        "authenticated",
        "insert",
        None,
        f"{APP_USER_ID} = updated_by",
        "allow insert when app.user_id matches updated_by; assumes per-connection app.user_id",
    )
    _create_policy(
        "platform_config",
        "authenticated",
        "update",
        f"{APP_USER_ID} = updated_by",
        f"{APP_USER_ID} = updated_by",
        "allow update when app.user_id matches updated_by; assumes per-connection app.user_id",
    )
    _create_policy(
        "platform_config",
        "authenticated",
        "delete",
        f"{APP_USER_ID} = updated_by",
        None,
        "allow delete when app.user_id matches updated_by; assumes per-connection app.user_id",
    )

    # audit_event: allow read/insert for owner or system context; deny updates/deletes
    _create_policy(
        "audit_event",
        "anon",
        "select",
        "false",
        None,
        "deny anon read access",
    )
    _create_policy(
        "audit_event",
        "anon",
        "insert",
        None,
        "false",
        "deny anon insert access",
    )
    _create_policy(
        "audit_event",
        "anon",
        "update",
        "false",
        "false",
        "deny anon update access",
    )
    _create_policy(
        "audit_event",
        "anon",
        "delete",
        "false",
        None,
        "deny anon delete access",
    )

    audit_condition = f"{APP_IS_SYSTEM} or ({APP_USER_ID} = actor_user_id)"
    _create_policy(
        "audit_event",
        "authenticated",
        "select",
        audit_condition,
        None,
        "allow read for matching user or system context; assumes app.user_id or app.is_system",
    )
    _create_policy(
        "audit_event",
        "authenticated",
        "insert",
        None,
        audit_condition,
        "allow insert for matching user or system context; assumes app.user_id or app.is_system",
    )
    _create_policy(
        "audit_event",
        "authenticated",
        "update",
        "false",
        "false",
        "deny updates to audit log to preserve immutability",
    )
    _create_policy(
        "audit_event",
        "authenticated",
        "delete",
        "false",
        None,
        "deny deletes to audit log to preserve immutability",
    )


def downgrade() -> None:
    # destructive rollback: drop rls policies, indexes, and tables
    # note: extensions and roles are left in place since they may be shared

    # drop optional index if it exists
    op.execute(
        """
-- drop optional trigram index if present
 drop index if exists ix_tag_name_trgm;
"""
    )

    # drop gin indexes
    op.drop_index("ix_audit_event_payload_gin", table_name="audit_event")
    op.drop_index("ix_job_error_payload_gin", table_name="job")
    op.drop_index("ix_qc_decision_payload_gin", table_name="qc_decision")
    op.drop_index("ix_render_metadata_json_gin", table_name="render")
    op.drop_index("ix_render_params_json_gin", table_name="render")

    # drop btree indexes
    op.drop_index("ix_job_stage_run_pipeline_stage", table_name="job_stage_run")
    op.drop_index("ix_job_status_updated_at", table_name="job")
    op.drop_index("ix_metrics_daily_render_date", table_name="metrics_daily")
    op.drop_index("ix_metrics_daily_platform_date", table_name="metrics_daily")
    op.drop_index("ix_publish_record_platform_published_at", table_name="publish_record")
    op.drop_index("ix_render_animation_id_created_at", table_name="render")
    op.drop_index("ix_animation_pipeline_stage_updated_at", table_name="animation")
    op.drop_index("ix_animation_status_created_at", table_name="animation")
    op.drop_index("ix_dsl_gap_status_updated_at", table_name="dsl_gap")
    op.drop_index("ix_idea_status_created_at", table_name="idea")

    # drop tables in reverse dependency order
    op.drop_table("audit_event")
    op.drop_table("platform_config")
    op.drop_table("job_stage_run")
    op.drop_table("job")
    op.drop_table("pipeline_run")
    op.drop_table("tag_event")
    op.drop_table("animation_tag")
    op.drop_table("tag")
    op.drop_table("metrics_daily")
    op.drop_table("metrics_pull_run")
    op.drop_table("publish_record")
    op.drop_table("qc_decision")
    op.drop_table("qc_checklist_item")
    op.drop_table("qc_checklist_version")
    op.drop_table("artifact")
    op.drop_table("render")
    op.drop_table("animation")
    op.drop_table("idea_embedding")
    op.drop_table("idea_similarity")
    op.drop_table("idea_gap_link")
    op.drop_table("dsl_gap")
    op.drop_table("idea")
    op.drop_table("idea_candidate")
    op.drop_table("idea_batch")
    op.drop_table("design_system_version")
    op.drop_table("dsl_version")
    op.drop_table("user_account")
