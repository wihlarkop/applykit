"""migrate_offer_status_to_negotiating

Revision ID: 4ac56bd7645a
Revises: 528ea0bbfe26
Create Date: 2026-08-28 18:35:30.130769

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ac56bd7645a'
down_revision: Union[str, Sequence[str], None] = '528ea0bbfe26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # "offer" is replaced by two stages, "negotiating" and "accepted"; existing
    # rows can't be known to have already reached "accepted", so they land on
    # the earlier, more general stage of the split.
    op.execute("UPDATE application SET status = 'negotiating' WHERE status = 'offer'")


def downgrade() -> None:
    """Downgrade schema."""
    # Both new stages collapse back to "offer"; the negotiating/accepted
    # distinction is lost, which is unavoidable for a status-split downgrade.
    op.execute(
        "UPDATE application SET status = 'offer' WHERE status IN ('negotiating', 'accepted')"
    )
