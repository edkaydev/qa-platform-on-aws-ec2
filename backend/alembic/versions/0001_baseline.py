"""Baseline schema for QAAI.

The baseline intentionally materialises the SQLAlchemy metadata so a fresh
database can be created through the migration pipeline rather than through
application startup. Subsequent changes should be generated with
``alembic revision --autogenerate``.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-10
"""

from alembic import op

from app import models  # noqa: F401
from app.db import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
