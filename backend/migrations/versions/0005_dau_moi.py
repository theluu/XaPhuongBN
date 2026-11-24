"""đầu mối và trách nhiệm chủ trì/phối hợp (DT V.1)

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')


def upgrade() -> None:
    op.create_table('dau_moi',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('ma', sa.String(length=30), nullable=False),
    sa.Column('ten', sa.String(length=300), nullable=False),
    sa.Column('cap', sa.String(length=20), nullable=False),
    sa.Column('noi_dung', sa.Text(), nullable=False),
    sa.Column('trach_nhiem', JSON, nullable=False),
    sa.Column('phieu_nguon', JSON, nullable=False),
    sa.Column('chi_tieu', JSON, nullable=False),
    sa.Column('nguon', JSON, nullable=False),
    sa.Column('nguoi_lien_he', sa.String(length=200), nullable=False),
    sa.Column('chuc_vu', sa.String(length=200), nullable=False),
    sa.Column('dien_thoai', sa.String(length=30), nullable=True),
    sa.Column('email', sa.String(length=200), nullable=True),
    sa.Column('user_ids', JSON, nullable=False),
    sa.Column('thu_tu', sa.Integer(), nullable=False),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('tenant_id', 'ma'),
    info={'rls': True}
    )
    op.create_index(op.f('ix_dau_moi_tenant_id'), 'dau_moi', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_dau_moi_is_sample'), 'dau_moi', ['is_sample'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_dau_moi_is_sample'), table_name='dau_moi')
    op.drop_index(op.f('ix_dau_moi_tenant_id'), table_name='dau_moi')
    op.drop_table('dau_moi')
