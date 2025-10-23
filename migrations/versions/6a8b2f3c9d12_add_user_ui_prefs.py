"""add_user_ui_prefs

Revision ID: 6a8b2f3c9d12
Revises: 47516bb30976
Create Date: 2025-10-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a8b2f3c9d12'
down_revision = '47516bb30976'
branch_labels = None
depends_on = None


def upgrade():
    # Add UI preference columns to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ui_duration_unit', sa.String(length=8), nullable=True, server_default='s'))
        batch_op.add_column(sa.Column('ui_verify_collapsed', sa.Boolean(), nullable=True, server_default=sa.sql.expression.false()))


def downgrade():
    # Remove UI preference columns
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('ui_verify_collapsed')
        batch_op.drop_column('ui_duration_unit')
