"""thông báo điều hành (dải bản tin)

Revision ID: 0006
Revises: 0005
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table('thong_bao',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('tieu_de', sa.String(length=300), nullable=False),
    sa.Column('noi_dung', sa.Text(), nullable=False),
    sa.Column('lien_ket', sa.String(length=500), nullable=True),
    sa.Column('muc_do', sa.String(length=20), nullable=False),
    sa.Column('tu_ngay', sa.Date(), nullable=False),
    sa.Column('den_ngay', sa.Date(), nullable=True),
    sa.Column('doi_tuong', JSON, nullable=False),
    sa.Column('ghim', sa.Boolean(), nullable=False),
    sa.Column('hien_tren_tv', sa.Boolean(), nullable=False),
    sa.Column('nguoi_tao_id', sa.Integer(), nullable=True),
    sa.Column('tao_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    info={'rls': True}
    )
    op.create_index(op.f('ix_thong_bao_tenant_id'), 'thong_bao', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_thong_bao_is_sample'), 'thong_bao', ['is_sample'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_thong_bao_is_sample'), table_name='thong_bao')
    op.drop_index(op.f('ix_thong_bao_tenant_id'), table_name='thong_bao')
    op.drop_table('thong_bao')
