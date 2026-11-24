"""thông báo cá nhân (chuông)

Revision ID: 0009
Revises: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('noti',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('tenant_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('loai', sa.String(length=30), nullable=False),
    sa.Column('tieu_de', sa.String(length=300), nullable=False),
    sa.Column('noi_dung', sa.Text(), nullable=False),
    sa.Column('lien_ket', sa.String(length=300), nullable=True),
    sa.Column('muc_do', sa.String(length=20), nullable=False),
    sa.Column('khoa', sa.String(length=120), nullable=True),
    sa.Column('tao_luc', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('da_doc_luc', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_sample', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    info={'rls': True})
    for c in ('tenant_id', 'user_id', 'khoa', 'tao_luc', 'is_sample'):
        op.create_index(op.f(f'ix_noti_{c}'), 'noti', [c], unique=False)


def downgrade() -> None:
    op.drop_table('noti')
