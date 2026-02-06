"""add carenderia_daily_expenses table

Revision ID: 209849050daf
Revises: 785f32636787
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "209849050daf"
down_revision = "785f32636787"
branch_labels = None
depends_on = None


def upgrade():
    # Create carenderia_daily_expenses table if it does not exist
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'carenderia_daily_expenses'
            ) THEN
                CREATE TABLE public.carenderia_daily_expenses (
                    id SERIAL PRIMARY KEY,
                    expense_type VARCHAR(100) NOT NULL UNIQUE,
                    amount NUMERIC(14,2) DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
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
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'carenderia_daily_expenses'
            ) THEN
                DROP TABLE public.carenderia_daily_expenses;
            END IF;
        END;
        $$;
        """
    )
