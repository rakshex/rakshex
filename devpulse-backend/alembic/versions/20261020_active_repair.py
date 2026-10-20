"""Enforce one active repair per workspace across concurrent API/worker processes."""
from alembic import op
import sqlalchemy as sa
revision='20261020_active_repair'
down_revision='20261020_repair_jobs'
branch_labels=None
depends_on=None


def upgrade():
    condition=sa.text("status IN ('queued','validating','publication_queued','publishing')")
    op.create_index('uq_repair_jobs_active_workspace','repair_jobs',['workspace_id'],unique=True,
                    sqlite_where=condition,postgresql_where=condition)


def downgrade():
    op.drop_index('uq_repair_jobs_active_workspace',table_name='repair_jobs')
