"""Add enriched doctor profile metadata for clinic data and leave status."""

from alembic import op
import sqlalchemy as sa


revision = "20260824_0002"
down_revision = "20240824_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("doctor_profiles", sa.Column("profile_photo_url", sa.String(length=500), nullable=True))
    op.add_column("doctor_profiles", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("doctor_profiles", sa.Column("languages", sa.String(length=255), nullable=True))
    op.add_column("doctor_profiles", sa.Column("consultation_fee", sa.Integer(), nullable=True, server_default="0"))
    op.add_column("doctor_profiles", sa.Column("clinic_name", sa.String(length=255), nullable=True))
    op.add_column("doctor_profiles", sa.Column("status", sa.String(length=50), nullable=True, server_default="available"))
    op.add_column("doctor_profiles", sa.Column("next_leave_date", sa.Date(), nullable=True))
    op.add_column("doctor_profiles", sa.Column("return_to_work_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("doctor_profiles", "return_to_work_date")
    op.drop_column("doctor_profiles", "next_leave_date")
    op.drop_column("doctor_profiles", "status")
    op.drop_column("doctor_profiles", "clinic_name")
    op.drop_column("doctor_profiles", "consultation_fee")
    op.drop_column("doctor_profiles", "languages")
    op.drop_column("doctor_profiles", "bio")
    op.drop_column("doctor_profiles", "profile_photo_url")
