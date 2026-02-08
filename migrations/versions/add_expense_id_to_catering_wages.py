"""add expense_id to catering_wages to link wage entries to CateringExpense

Revision ID: a1b2c3d4e6f7
Revises: 785f32636787
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e6f7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'catering_wages'
                  AND column_name = 'expense_id'
            ) THEN
                ALTER TABLE public.catering_wages
                    ADD COLUMN expense_id INTEGER NULL REFERENCES catering_expense(id) ON DELETE SET NULL;
            END IF;
        END;
        $$;
        """
    )


def downgrade():
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'catering_wages'
                  AND column_name = 'expense_id'
            ) THEN
                ALTER TABLE public.catering_wages DROP COLUMN expense_id;
            END IF;
        END;
        $$;
        """
    )
