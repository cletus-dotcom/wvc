"""add overtime_hours and overtime_amount to project_expenses

Revision ID: 785f32636787
Revises: e749b01e5ffd
Create Date: 2026-02-05

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "785f32636787"
down_revision = "e749b01e5ffd"
branch_labels = None
depends_on = None


def upgrade():
    # Add overtime columns if they do not exist (idempotent for Supabase/Postgres)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'project_expenses'
                  AND column_name = 'overtime_hours'
            ) THEN
                ALTER TABLE public.project_expenses
                    ADD COLUMN overtime_hours NUMERIC(12,3) NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'project_expenses'
                  AND column_name = 'overtime_amount'
            ) THEN
                ALTER TABLE public.project_expenses
                    ADD COLUMN overtime_amount NUMERIC(14,2) NULL;
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
                  AND table_name = 'project_expenses'
                  AND column_name = 'overtime_hours'
            ) THEN
                ALTER TABLE public.project_expenses DROP COLUMN overtime_hours;
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'project_expenses'
                  AND column_name = 'overtime_amount'
            ) THEN
                ALTER TABLE public.project_expenses DROP COLUMN overtime_amount;
            END IF;
        END;
        $$;
        """
    )
