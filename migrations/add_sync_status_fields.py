"""
Add sync status fields to User model
"""

import sqlalchemy as sa
from alembic import op

def upgrade():
    """Add sync status fields to user table."""
    # Add new columns to user table
    op.add_column('user', sa.Column('canvas_last_sync_courses', sa.Integer(), nullable=True, default=0))
    op.add_column('user', sa.Column('canvas_last_sync_assignments', sa.Integer(), nullable=True, default=0))
    op.add_column('user', sa.Column('canvas_last_sync_categories', sa.Integer(), nullable=True, default=0))
    op.add_column('user', sa.Column('canvas_sync_status', sa.String(length=50), nullable=True, default='idle'))

def downgrade():
    """Remove sync status fields from user table."""
    op.drop_column('user', 'canvas_sync_status')
    op.drop_column('user', 'canvas_last_sync_categories')
    op.drop_column('user', 'canvas_last_sync_assignments')
    op.drop_column('user', 'canvas_last_sync_courses')