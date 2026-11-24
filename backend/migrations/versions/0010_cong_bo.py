"""bản công bố kỳ cho trang công khai theo phường

Revision ID: 0010
Revises: 0009
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table('cong_bo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('ky', sa.String(length=10), nullable=False),
    sa.Column('du_lieu', JSON, nullable=False),
    sa.Column('nguoi_cong_bo_id', sa.Integer(), nullable=True),
    sa.Column('nguoi_cong_bo_ten', sa.String(length=200), nullable=False),
    sa.Column('cong_bo_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('thu_hoi_luc', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    info={'rls': True})
    for c in ('tenant_id', 'ky', 'cong_bo_luc', 'is_sample'):
        op.create_index(op.f(f'ix_cong_bo_{c}'), 'cong_bo', [c], unique=False)


def downgrade() -> None:
    op.drop_table('cong_bo')
