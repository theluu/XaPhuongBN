"""phản ánh hiện trường; thông tin thôn/tổ dân phố

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.add_column('residential_group', sa.Column('loai', sa.String(length=10), nullable=True))
    op.add_column('residential_group', sa.Column('nguoi_dung_dau', sa.String(length=200), nullable=True))
    op.add_column('residential_group', sa.Column('dien_thoai', sa.String(length=30), nullable=True))
    op.add_column('residential_group', sa.Column('lat', sa.Numeric(9, 6), nullable=True))
    op.add_column('residential_group', sa.Column('lng', sa.Numeric(9, 6), nullable=True))
    op.add_column('residential_group', sa.Column('ngung_hoat_dong', sa.Boolean(), nullable=True))
    op.create_table('field_report',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('ma', sa.String(length=40), nullable=False),
    sa.Column('tieu_de', sa.String(length=300), nullable=False),
    sa.Column('mo_ta', sa.Text(), nullable=False),
    sa.Column('linh_vuc', sa.String(length=40), nullable=False),
    sa.Column('nguon', sa.String(length=30), nullable=False),
    sa.Column('khan_cap', sa.Boolean(), nullable=False),
    sa.Column('tdp_id', sa.Integer(), nullable=True),
    sa.Column('dia_chi', sa.String(length=300), nullable=False),
    sa.Column('lat', sa.Numeric(9, 6), nullable=True),
    sa.Column('lng', sa.Numeric(9, 6), nullable=True),
    sa.Column('anh_keys', JSON, nullable=False),
    sa.Column('nguoi_gui_ten', sa.String(length=200), nullable=True),
    sa.Column('nguoi_gui_sdt', sa.String(length=30), nullable=True),
    sa.Column('don_vi_phu_trach', sa.String(length=20), nullable=True),
    sa.Column('nguoi_phu_trach', sa.String(length=200), nullable=True),
    sa.Column('chi_dao', sa.Text(), nullable=False),
    sa.Column('han_xu_ly', sa.Date(), nullable=True),
    sa.Column('trang_thai', sa.String(length=20), nullable=False),
    sa.Column('tien_do_pct', sa.Integer(), nullable=False),
    sa.Column('ket_qua', sa.Text(), nullable=False),
    sa.Column('anh_ket_qua_keys', JSON, nullable=False),
    sa.Column('tiep_nhan_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('hoan_thanh_luc', sa.DateTime(timezone=True), nullable=True),
    sa.Column('cap_nhat_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('nguoi_tiep_nhan_id', sa.Integer(), nullable=True),
    sa.Column('lich_su', JSON, nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'ma'),
    info={'rls': True}
    )
    for col in ('tenant_id', 'tdp_id', 'han_xu_ly', 'trang_thai', 'is_sample'):
        op.create_index(op.f(f'ix_field_report_{col}'), 'field_report', [col], unique=False)


def downgrade() -> None:
    op.drop_table('field_report')
    for col in ('ngung_hoat_dong', 'lng', 'lat', 'dien_thoai', 'nguoi_dung_dau', 'loai'):
        op.drop_column('residential_group', col)
