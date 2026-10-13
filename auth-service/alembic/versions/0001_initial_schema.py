"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-29
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vendors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("bcrypt_password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, default=True),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vendor_id", sa.Integer, sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("uuid_hash", sa.String(64), nullable=False),
        sa.Column("totp_seed_hash", sa.String(512), nullable=False),
        sa.Column("enrolled_at", sa.DateTime, nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, default=False),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("last_used_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "enrollment_tokens",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("vendor_id", sa.Integer, sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, default=False),
        sa.Column("used_at", sa.DateTime, nullable=True),
    )
    op.create_table(
        "auth_attempts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("vendor_id", sa.Integer, sa.ForeignKey("vendors.id"), nullable=False),
        sa.Column("attempted_at", sa.DateTime, nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("failure_reason", sa.String(128), nullable=True),
    )
    op.create_table(
        "admins",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(128), nullable=False, unique=True),
        sa.Column("bcrypt_password_hash", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, default=True),
    )
    op.create_table(
        "admin_attempts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("admin_id", sa.Integer, sa.ForeignKey("admins.id"), nullable=False),
        sa.Column("attempted_at", sa.DateTime, nullable=False),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("failure_reason", sa.String(128), nullable=True),
    )
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("session_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("subject_id", sa.Integer, nullable=False),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("last_active_at", sa.DateTime, nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("invalidated", sa.Boolean, nullable=False, default=False),
        sa.Column("source_ip", sa.String(45), nullable=True),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("subject_id", sa.Integer, nullable=False),
        sa.Column("subject_type", sa.String(16), nullable=False),
        sa.Column("vendor_id", sa.Integer, nullable=True),
        sa.Column("device_uuid_hash", sa.String(64), nullable=True),
        sa.Column("action_detail", sa.JSON, nullable=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("source_ip", sa.String(45), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("sessions")
    op.drop_table("admin_attempts")
    op.drop_table("admins")
    op.drop_table("auth_attempts")
    op.drop_table("enrollment_tokens")
    op.drop_table("devices")
    op.drop_table("vendors")
