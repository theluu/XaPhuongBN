"""cơ cấu tổ chức: đơn vị, cán bộ

Revision ID: 0004
Revises: 0003
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table('org_unit',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('ma', sa.String(length=20), nullable=False),
    sa.Column('ten', sa.String(length=200), nullable=False),
    sa.Column('khoi', sa.String(length=20), nullable=False),
    sa.Column('cap_tren_ma', sa.String(length=20), nullable=True),
    sa.Column('lanh_dao_phu_trach_ma', sa.String(length=20), nullable=True),
    sa.Column('chuc_nang', sa.Text(), nullable=False),
    sa.Column('dien_thoai', sa.String(length=30), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('dia_chi', sa.String(length=300), nullable=True),
    sa.Column('thu_tu', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'ma'),
    info={'rls': True}
    )
    op.create_index(op.f('ix_org_unit_tenant_id'), 'org_unit', ['tenant_id'], unique=False)
    op.create_table('org_staff',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('ma', sa.String(length=20), nullable=False),
    sa.Column('don_vi_ma', sa.String(length=20), nullable=False),
    sa.Column('ho_ten', sa.String(length=200), nullable=False),
    sa.Column('chuc_vu', sa.String(length=200), nullable=False),
    sa.Column('cap', sa.String(length=20), nullable=False),
    sa.Column('dien_thoai', sa.String(length=30), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('nhiem_vu', sa.Text(), nullable=False),
    sa.Column('linh_vuc', JSON, nullable=False),
    sa.Column('dia_ban_ids', JSON, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('thu_tu', sa.Integer(), nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'ma'),
    info={'rls': True}
    )
    for col in ('tenant_id', 'don_vi_ma', 'is_sample'):
        op.create_index(op.f(f'ix_org_staff_{col}'), 'org_staff', [col], unique=False)


def downgrade() -> None:
    op.drop_table('org_staff')
    op.drop_table('org_unit')
