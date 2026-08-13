"""Initial LocalPDF schema and immutable audit guards."""

from alembic import op

from app.infrastructure.db.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION localpdf_reject_mutation()
        RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'LocalPDF immutable row cannot be changed';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER events_append_only
        BEFORE UPDATE OR DELETE ON events
        FOR EACH ROW EXECUTE FUNCTION localpdf_reject_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER originals_immutable
        BEFORE UPDATE OR DELETE ON originals
        FOR EACH ROW EXECUTE FUNCTION localpdf_reject_mutation();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    op.execute("DROP TRIGGER IF EXISTS events_append_only ON events")
    op.execute("DROP TRIGGER IF EXISTS originals_immutable ON originals")
    op.execute("DROP FUNCTION IF EXISTS localpdf_reject_mutation")
    Base.metadata.drop_all(bind=bind)
