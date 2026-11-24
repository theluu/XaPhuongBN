"""nhắn tin nội bộ, tệp đính kèm, công văn xử lý qua tin nhắn

Revision ID: 0008
Revises: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def _base() -> list:
    return [sa.Column('id', sa.Integer(), nullable=False), sa.Column('tenant_id', sa.Integer(), nullable=False)]


def _end() -> list:
    return [sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'), sa.PrimaryKeyConstraint('id')]


def upgrade() -> None:
    op.create_table('hoi_thoai', *_base(),
    sa.Column('tieu_de', sa.String(length=300), nullable=False),
    sa.Column('loai', sa.String(length=20), nullable=False),
    sa.Column('lien_ket_loai', sa.String(length=20), nullable=True),
    sa.Column('lien_ket_id', sa.Integer(), nullable=True),
    sa.Column('lien_ket_ten', sa.String(length=500), nullable=True),
    sa.Column('lien_ket_url', sa.String(length=300), nullable=True),
    sa.Column('tao_boi', sa.Integer(), nullable=False),
    sa.Column('tao_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('cap_nhat_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    *_end(), info={'rls': True})
    for c in ('tenant_id', 'lien_ket_id', 'cap_nhat_luc', 'is_sample'):
        op.create_index(op.f(f'ix_hoi_thoai_{c}'), 'hoi_thoai', [c], unique=False)
    op.create_table('hoi_thoai_thanh_vien', *_base(),
    sa.Column('hoi_thoai_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('doc_den', sa.Integer(), nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    *_end(), sa.ForeignKeyConstraint(['hoi_thoai_id'], ['hoi_thoai.id'], ondelete='CASCADE'),
    sa.UniqueConstraint('hoi_thoai_id', 'user_id'), info={'rls': True})
    for c in ('tenant_id', 'hoi_thoai_id', 'user_id', 'is_sample'):
        op.create_index(op.f(f'ix_hoi_thoai_thanh_vien_{c}'), 'hoi_thoai_thanh_vien', [c], unique=False)
    op.create_table('tin_nhan', *_base(),
    sa.Column('hoi_thoai_id', sa.Integer(), nullable=False),
    sa.Column('nguoi_gui_id', sa.Integer(), nullable=False),
    sa.Column('noi_dung', sa.Text(), nullable=False),
    sa.Column('van_ban_id', sa.Integer(), nullable=True),
    sa.Column('he_thong', sa.Boolean(), nullable=False),
    sa.Column('gui_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    *_end(), sa.ForeignKeyConstraint(['hoi_thoai_id'], ['hoi_thoai.id'], ondelete='CASCADE'), info={'rls': True})
    for c in ('tenant_id', 'hoi_thoai_id', 'is_sample'):
        op.create_index(op.f(f'ix_tin_nhan_{c}'), 'tin_nhan', [c], unique=False)
    op.create_table('tin_nhan_tep', *_base(),
    sa.Column('tin_nhan_id', sa.Integer(), nullable=False),
    sa.Column('hoi_thoai_id', sa.Integer(), nullable=False),
    sa.Column('key', sa.String(length=80), nullable=False),
    sa.Column('ten', sa.String(length=300), nullable=False),
    sa.Column('content_type', sa.String(length=100), nullable=False),
    sa.Column('kich_thuoc', sa.Integer(), nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    *_end(), sa.ForeignKeyConstraint(['tin_nhan_id'], ['tin_nhan.id'], ondelete='CASCADE'), info={'rls': True})
    for c in ('tenant_id', 'tin_nhan_id', 'hoi_thoai_id', 'key', 'is_sample'):
        op.create_index(op.f(f'ix_tin_nhan_tep_{c}'), 'tin_nhan_tep', [c], unique=False)


def downgrade() -> None:
    for t in ('tin_nhan_tep', 'tin_nhan', 'hoi_thoai_thanh_vien', 'hoi_thoai'):
        op.drop_table(t)
