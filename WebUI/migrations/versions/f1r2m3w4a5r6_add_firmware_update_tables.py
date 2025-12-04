"""add firmware update tables

Revision ID: f1r2m3w4a5r6
Revises: d7e8f9a0b1c2
Create Date: 2025-12-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1r2m3w4a5r6'
down_revision = 'd7e8f9a0b1c2'
branch_labels = None
depends_on = None


def upgrade():
    # Add firmware_version column to robot table
    with op.batch_alter_table('robot', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('firmware_version', sa.String(length=32), nullable=True)
        )

    # Create firmware_version table
    op.create_table(
        'firmware_version',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=32), nullable=False),
        sa.Column('robot_type', sa.String(length=64), nullable=False),
        sa.Column('release_notes', sa.Text(), nullable=True),
        sa.Column('download_url', sa.String(length=512), nullable=True),
        sa.Column('checksum', sa.String(length=128), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('is_stable', sa.Boolean(), nullable=True),
        sa.Column('min_required_version', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version', 'robot_type', name='uq_firmware_version_type')
    )
    with op.batch_alter_table('firmware_version', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_firmware_version_created_at'),
            ['created_at'],
            unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_firmware_version_robot_type'),
            ['robot_type'],
            unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_firmware_version_version'),
            ['version'],
            unique=False
        )

    # Create firmware_update table
    op.create_table(
        'firmware_update',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('robot_id', sa.Integer(), nullable=False),
        sa.Column('firmware_version_id', sa.Integer(), nullable=False),
        sa.Column('initiated_by', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('previous_version', sa.String(length=32), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['firmware_version_id'], ['firmware_version.id'], ),
        sa.ForeignKeyConstraint(['initiated_by'], ['user.id'], ),
        sa.ForeignKeyConstraint(['robot_id'], ['robot.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('firmware_update', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_firmware_update_robot_id'),
            ['robot_id'],
            unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_firmware_update_status'),
            ['status'],
            unique=False
        )


def downgrade():
    # Drop firmware_update table
    with op.batch_alter_table('firmware_update', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_firmware_update_status'))
        batch_op.drop_index(batch_op.f('ix_firmware_update_robot_id'))
    op.drop_table('firmware_update')

    # Drop firmware_version table
    with op.batch_alter_table('firmware_version', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_firmware_version_version'))
        batch_op.drop_index(batch_op.f('ix_firmware_version_robot_type'))
        batch_op.drop_index(batch_op.f('ix_firmware_version_created_at'))
    op.drop_table('firmware_version')

    # Remove firmware_version column from robot table
    with op.batch_alter_table('robot', schema=None) as batch_op:
        batch_op.drop_column('firmware_version')
