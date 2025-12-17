"""add_audit_log_table

Revision ID: a1u2d3i4t5l6
Revises: f1r2m3w4a5r6
Create Date: 2025-12-17 02:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1u2d3i4t5l6'
down_revision = 'f1r2m3w4a5r6'
branch_labels = None
depends_on = None


def upgrade():
    # Create audit_log table
    op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trace_id', sa.String(length=64), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('category', sa.String(length=32), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context', sa.JSON(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=True),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_audit_timestamp_severity', 'audit_log', ['timestamp', 'severity'], unique=False)
    op.create_index('idx_audit_user_action', 'audit_log', ['user_id', 'action'], unique=False)
    op.create_index('idx_audit_category_timestamp', 'audit_log', ['category', 'timestamp'], unique=False)
    op.create_index(op.f('ix_audit_log_trace_id'), 'audit_log', ['trace_id'], unique=False)
    op.create_index(op.f('ix_audit_log_timestamp'), 'audit_log', ['timestamp'], unique=False)
    op.create_index(op.f('ix_audit_log_severity'), 'audit_log', ['severity'], unique=False)
    op.create_index(op.f('ix_audit_log_category'), 'audit_log', ['category'], unique=False)
    op.create_index(op.f('ix_audit_log_user_id'), 'audit_log', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_audit_log_action'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_user_id'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_category'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_severity'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_timestamp'), table_name='audit_log')
    op.drop_index(op.f('ix_audit_log_trace_id'), table_name='audit_log')
    op.drop_index('idx_audit_category_timestamp', table_name='audit_log')
    op.drop_index('idx_audit_user_action', table_name='audit_log')
    op.drop_index('idx_audit_timestamp_severity', table_name='audit_log')
    
    # Drop table
    op.drop_table('audit_log')
