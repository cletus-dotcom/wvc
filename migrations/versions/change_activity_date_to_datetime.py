"""Change activity_date from Date to DateTime

Revision ID: a1b2c3d4e5f6
Revises: 442607d26bcb
Create Date: 2025-12-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '442607d26bcb'
branch_labels = None
depends_on = None


def upgrade():
    # Change activity_date column from Date to DateTime
    with op.batch_alter_table('project_expenses', schema=None) as batch_op:
        # For PostgreSQL, we can use ALTER COLUMN TYPE
        # For other databases, this might need different syntax
        batch_op.alter_column('activity_date',
               existing_type=sa.Date(),
               type_=sa.DateTime(),
               existing_nullable=True)


def downgrade():
    # Revert activity_date column from DateTime back to Date
    with op.batch_alter_table('project_expenses', schema=None) as batch_op:
        batch_op.alter_column('activity_date',
               existing_type=sa.DateTime(),
               type_=sa.Date(),
               existing_nullable=True)

