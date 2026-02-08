"""add catering_expense reference_number, booking_id and catering_purchase_items table

Revision ID: c1d2e3f4a5b6
Revises: b8c4e5f6a7d9
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


revision = "c1d2e3f4a5b6"
down_revision = "b8c4e5f6a7d9"
branch_labels = None
depends_on = None


def upgrade():
    # Add reference_number and booking_id to catering_expense
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'catering_expense' AND column_name = 'reference_number'
            ) THEN
                ALTER TABLE catering_expense ADD COLUMN reference_number VARCHAR(100) NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'catering_expense' AND column_name = 'booking_id'
            ) THEN
                ALTER TABLE catering_expense ADD COLUMN booking_id INTEGER NULL REFERENCES catering_requests(id);
            END IF;
        END $$;
        """
    )
    op.create_table(
        "catering_purchase_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("expense_id", sa.Integer(), sa.ForeignKey("catering_expense.id", ondelete="CASCADE"), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("qty", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table("catering_purchase_items")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'catering_expense' AND column_name = 'reference_number') THEN
                ALTER TABLE catering_expense DROP COLUMN reference_number;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'catering_expense' AND column_name = 'booking_id') THEN
                ALTER TABLE catering_expense DROP COLUMN booking_id;
            END IF;
        END $$;
        """
    )
