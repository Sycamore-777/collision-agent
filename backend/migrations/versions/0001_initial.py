"""Initial task, parsing, event, and artifact tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=False),
    )

    op.create_table(
        "task_input",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("input_type", sa.String(length=32), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("source_name", sa.String(length=255), nullable=True),
        sa.Column("file_hash", sa.String(length=128), nullable=True),
        sa.Column("confidentiality", sa.String(length=32), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "parsed_document",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("parser_name", sa.String(length=64), nullable=False),
        sa.Column("parse_status", sa.String(length=32), nullable=False),
        sa.Column("output_path", sa.Text(), nullable=False),
        sa.Column("confidence_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "event_record",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("message_id", sa.String(length=128), nullable=True),
        sa.Column("conjunction_id", sa.String(length=128), nullable=True),
        sa.Column("primary_object_name", sa.String(length=255), nullable=True),
        sa.Column("secondary_object_name", sa.String(length=255), nullable=True),
        sa.Column("primary_norad_id", sa.String(length=64), nullable=True),
        sa.Column("secondary_norad_id", sa.String(length=64), nullable=True),
        sa.Column("tca_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("miss_distance_m", sa.Float(), nullable=True),
        sa.Column("relative_speed_mps", sa.Float(), nullable=True),
        sa.Column("collision_probability", sa.Float(), nullable=True),
        sa.Column("reference_frame", sa.String(length=64), nullable=True),
        sa.Column("covariance_present", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("action_recommendation", sa.Text(), nullable=True),
        sa.Column("needs_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("version_group_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "llm_call_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(length=64), nullable=False),
        sa.Column("provider_name", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("parsed_output_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "task_step_log",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(length=64), nullable=False),
        sa.Column("step_status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_ref", sa.Text(), nullable=True),
        sa.Column("output_ref", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "report_record",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("task_id", sa.String(length=36), sa.ForeignKey("task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_path", sa.Text(), nullable=False),
        sa.Column("result_json_path", sa.Text(), nullable=False),
        sa.Column("trace_json_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("report_record")
    op.drop_table("task_step_log")
    op.drop_table("llm_call_log")
    op.drop_table("event_record")
    op.drop_table("parsed_document")
    op.drop_table("task_input")
    op.drop_table("task")

