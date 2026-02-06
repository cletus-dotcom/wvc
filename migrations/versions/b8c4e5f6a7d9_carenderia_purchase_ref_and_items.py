"""add carenderia transaction reference_number and purchase_items table

Revision ID: b8c4e5f6a7d9
Revises: 209849050daf
Create Date: 2026-02-06

"""
from alembic import op
import sqlalchemy as sa


revision = "b8c4e5f6a7d9"
down_revision = "209849050daf"
branch_labels = None
depends_on = None


def upgrade():
    # Add reference_number to carenderia_transaction
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carenderia_transaction' AND column_name = 'reference_number'
            ) THEN
                ALTER TABLE carenderia_transaction ADD COLUMN reference_number VARCHAR(100) NULL;
            END IF;
        END $$;
        """
    )
    # Create carenderia_purchase_items table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS carenderia_purchase_items (
            id BIGSERIAL PRIMARY KEY,
            trans_id BIGINT NOT NULL REFERENCES carenderia_transaction(id) ON DELETE CASCADE,
            description VARCHAR(255),
            qty NUMERIC(12,3) NOT NULL DEFAULT 0,
            unit VARCHAR(50),
            unit_price NUMERIC(14,2) NOT NULL DEFAULT 0,
            amount NUMERIC(14,2) NOT NULL DEFAULT 0
        );
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS carenderia_purchase_items;")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'carenderia_transaction' AND column_name = 'reference_number'
            ) THEN
                ALTER TABLE carenderia_transaction DROP COLUMN reference_number;
            END IF;
        END $$;
        """
    )
