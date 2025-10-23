"""create adv command tables

Revision ID: 0001_create_adv_command_tables
Revises: 
Create Date: 2025-10-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, Text

# revision identifiers, used by Alembic.
revision = '0001_create_adv_command_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create table adv_command
    op.create_table(
        'adv_command',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create table advanced_command_version
    op.create_table(
        'advanced_command_version',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('advanced_command_id', sa.Integer(), nullable=False),
        sa.Column('adv_command_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # NOTE: If AdvancedCommand table already exists, migration should be adapted to
    # create the versions table and move existing base_commands into adv_command
    # and create an initial version. The repo's current models keep legacy fields
    # in AdvancedCommand; this migration only creates new tables.


def downgrade():
    op.drop_table('advanced_command_version')
    op.drop_table('adv_command')
