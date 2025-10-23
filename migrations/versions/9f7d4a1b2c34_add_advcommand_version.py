"""add_advcommand_version

Revision ID: 9f7d4a1b2c34
Revises: 6a8b2f3c9d12
Create Date: 2025-10-22 00:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f7d4a1b2c34'
down_revision = '6a8b2f3c9d12'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('advanced_command', schema=None) as batch_op:
        batch_op.add_column(sa.Column('version', sa.Integer(), nullable=True, server_default='1'))


def downgrade():
    with op.batch_alter_table('advanced_command', schema=None) as batch_op:
        batch_op.drop_column('version')
