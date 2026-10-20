"""Encrypted repair artifacts and validation/publication state machine."""
from alembic import op
import sqlalchemy as sa
revision='20261020_repair_jobs'
down_revision='20261020_repair_analysis'
branch_labels=None
depends_on=None


def upgrade():
    op.create_table('repair_jobs',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('workspace_id',sa.String(64),sa.ForeignKey('teams.id',ondelete='CASCADE'),nullable=False),
        sa.Column('actor_id',sa.BigInteger,sa.ForeignKey('users.id',ondelete='CASCADE'),nullable=False),
        sa.Column('status',sa.String(32),nullable=False),sa.Column('sealed_bundle',sa.Text,nullable=False),
        sa.Column('patch_hash',sa.String(64),nullable=False),sa.Column('report',sa.JSON,nullable=False),
        sa.Column('approved_by',sa.BigInteger,sa.ForeignKey('users.id',ondelete='SET NULL')),
        sa.Column('approval_hash',sa.String(64)),
        sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column('updated_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index('ix_repair_jobs_workspace_created','repair_jobs',['workspace_id','created_at'])


def downgrade():
    op.drop_index('ix_repair_jobs_workspace_created',table_name='repair_jobs')
    op.drop_table('repair_jobs')
