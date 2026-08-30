"""Initial persistence and audit boundaries.

Revision ID: 20260829_0001
Revises:
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260829_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversation_states",
        sa.Column("conversation_id", sa.String(200), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 0", name="ck_conversation_revision_nonnegative"),
    )
    op.create_table(
        "source_documents",
        sa.Column("document_id", sa.String(200), primary_key=True),
        sa.Column("content_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ingestion_records",
        sa.Column("ingestion_id", sa.String(200), primary_key=True),
        sa.Column("document_id", sa.String(200), sa.ForeignKey("source_documents.document_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("revision >= 0", name="ck_ingestion_revision_nonnegative"),
    )
    op.create_table(
        "published_scheme_versions",
        sa.Column("publication_id", sa.String(200), primary_key=True),
        sa.Column("scheme_id", sa.String(200), nullable=False),
        sa.Column("version_id", sa.String(200), nullable=False),
        sa.Column("human_review_id", sa.String(200), nullable=False),
        sa.Column("published_by", sa.String(200), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("record", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint("scheme_id", "version_id", name="uq_published_scheme_version"),
    )
    op.create_index("ix_published_scheme_active", "published_scheme_versions", ["scheme_id", "published_at"])
    op.create_table(
        "published_document_chunks",
        sa.Column("chunk_id", sa.String(200), primary_key=True),
        sa.Column("publication_id", sa.String(200), sa.ForeignKey("published_scheme_versions.publication_id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", sa.String(200), sa.ForeignKey("source_documents.document_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_ref_id", sa.String(200), nullable=False),
        sa.Column("locator", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_published_chunks_publication", "published_document_chunks", ["publication_id", "ordinal"])
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(200), primary_key=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.String(200), nullable=False),
        sa.Column("action", sa.String(200), nullable=False),
        sa.Column("target_type", sa.String(100), nullable=False),
        sa.Column("target_id", sa.String(300), nullable=False),
        sa.Column("request_id", sa.String(200), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index("ix_audit_target", "audit_events", ["target_type", "target_id", "occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_target", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_published_chunks_publication", table_name="published_document_chunks")
    op.drop_table("published_document_chunks")
    op.drop_index("ix_published_scheme_active", table_name="published_scheme_versions")
    op.drop_table("published_scheme_versions")
    op.drop_table("ingestion_records")
    op.drop_table("source_documents")
    op.drop_table("conversation_states")
