"""add device binding

Revision ID: 20260211075808
Revises: f1r2m3w4a5r6
Create Date: 2026-02-11 07:58:08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260211075808'
down_revision = 'f1r2m3w4a5r6'
branch_labels = None
depends_on = None


def upgrade():
    # Create device table
    op.create_table(
        'device',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.String(length=64), nullable=False),
        sa.Column('device_name', sa.String(length=128), nullable=True),
        sa.Column('device_type', sa.String(length=32), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bound_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_trusted', sa.Boolean(), nullable=True),
        sa.Column('platform', sa.String(length=32), nullable=True),
        sa.Column('hostname', sa.String(length=128), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_device_device_id'), 'device', ['device_id'], unique=True)
    op.create_index(op.f('ix_device_user_id'), 'device', ['user_id'], unique=False)
    op.create_index(op.f('ix_device_is_active'), 'device', ['is_active'], unique=False)
    op.create_index(op.f('ix_device_created_at'), 'device', ['created_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_device_created_at'), table_name='device')
    op.drop_index(op.f('ix_device_is_active'), table_name='device')
    op.drop_index(op.f('ix_device_user_id'), table_name='device')
    op.drop_index(op.f('ix_device_device_id'), table_name='device')
    
    # Drop table
    op.drop_table('device')
