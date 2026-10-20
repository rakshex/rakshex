"""Add minimal workspace-scoped contract analysis evidence."""
from alembic import op
import sqlalchemy as sa

revision = "20261020_repair_analysis"
down_revision = "002_onboarding_progress"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("repair_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(64), sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.BigInteger, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report", sa.JSON, nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_repair_analyses_workspace_created", "repair_analyses", ["workspace_id", "created_at"])


def downgrade():
    op.drop_index("ix_repair_analyses_workspace_created", table_name="repair_analyses")
    op.drop_table("repair_analyses")
