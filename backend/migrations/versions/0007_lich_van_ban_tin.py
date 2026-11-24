"""lịch công tác, văn bản chỉ đạo điều hành, tin từ nguồn RSS/Atom

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def _tenant() -> list:
    return [sa.Column('id', sa.Integer(), nullable=False), sa.Column('tenant_id', sa.Integer(), nullable=False)]


def _end() -> list:
    return [sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'), sa.PrimaryKeyConstraint('id')]


def upgrade() -> None:
    op.create_table('lich_cong_tac', *_tenant(),
    sa.Column('ngay', sa.Date(), nullable=False),
    sa.Column('gio_bat_dau', sa.String(length=5), nullable=False),
    sa.Column('gio_ket_thuc', sa.String(length=5), nullable=True),
    sa.Column('noi_dung', sa.Text(), nullable=False),
    sa.Column('chu_tri', sa.String(length=200), nullable=False),
    sa.Column('dia_diem', sa.String(length=300), nullable=False),
    sa.Column('thanh_phan', sa.Text(), nullable=False),
    sa.Column('don_vi_chuan_bi', sa.String(length=300), nullable=False),
    sa.Column('loai', sa.String(length=20), nullable=False),
    sa.Column('trang_thai', sa.String(length=20), nullable=False),
    sa.Column('hien_tren_tv', sa.Boolean(), nullable=False),
    sa.Column('ghi_chu', sa.Text(), nullable=False),
    sa.Column('nguoi_tao_id', sa.Integer(), nullable=True),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    *_end(), info={'rls': True})
    for c in ('tenant_id', 'ngay', 'is_sample'):
        op.create_index(op.f(f'ix_lich_cong_tac_{c}'), 'lich_cong_tac', [c], unique=False)
    op.create_table('van_ban', *_tenant(),
    sa.Column('so_ky_hieu', sa.String(length=100), nullable=False),
    sa.Column('ngay_ban_hanh', sa.Date(), nullable=False),
    sa.Column('loai', sa.String(length=20), nullable=False),
    sa.Column('co_quan_ban_hanh', sa.String(length=300), nullable=False),
    sa.Column('nguoi_ky', sa.String(length=200), nullable=False),
    sa.Column('trich_yeu', sa.Text(), nullable=False),
    sa.Column('file_key', sa.String(length=80), nullable=True),
    sa.Column('lien_ket', sa.String(length=500), nullable=True),
    sa.Column('han_thuc_hien', sa.Date(), nullable=True),
    sa.Column('trang_thai', sa.String(length=20), nullable=False),
    sa.Column('nhiem_vu_ids', JSON, nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    *_end(), info={'rls': True})
    for c in ('tenant_id', 'ngay_ban_hanh', 'is_sample'):
        op.create_index(op.f(f'ix_van_ban_{c}'), 'van_ban', [c], unique=False)
    op.create_table('tin_ngoai', *_tenant(),
    sa.Column('nguon', sa.String(length=500), nullable=False),
    sa.Column('ten_nguon', sa.String(length=200), nullable=False),
    sa.Column('guid', sa.String(length=500), nullable=False),
    sa.Column('tieu_de', sa.String(length=500), nullable=False),
    sa.Column('lien_ket', sa.String(length=500), nullable=False),
    sa.Column('ngay_dang', sa.DateTime(timezone=True), nullable=True),
    sa.Column('lay_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    *_end(), sa.UniqueConstraint('tenant_id', 'guid'), info={'rls': True})
    for c in ('tenant_id', 'ngay_dang'):
        op.create_index(op.f(f'ix_tin_ngoai_{c}'), 'tin_ngoai', [c], unique=False)


def downgrade() -> None:
    for t in ('tin_ngoai', 'van_ban', 'lich_cong_tac'):
        op.drop_table(t)
