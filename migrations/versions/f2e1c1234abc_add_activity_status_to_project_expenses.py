"""add activity_status column to project_expenses

Revision ID: f2e1c1234abc
Revises: ee24f4701032
Create Date: 2026-02-05

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "f2e1c1234abc"
down_revision = "ee24f4701032"
branch_labels = None
depends_on = None


def upgrade():
    # Add activity_status if it does not exist (idempotent)
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'project_expenses'
                  AND column_name = 'activity_status'
            ) THEN
                ALTER TABLE public.project_expenses
                    ADD COLUMN activity_status VARCHAR(50) DEFAULT 'Pending';
            END IF;
        END;
        $$;
        """
    )


def downgrade():
    # Drop activity_status if it exists
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'project_expenses'
                  AND column_name = 'activity_status'
            ) THEN
                ALTER TABLE public.project_expenses
                    DROP COLUMN activity_status;
            END IF;
        END;
        $$;
        """
    )
