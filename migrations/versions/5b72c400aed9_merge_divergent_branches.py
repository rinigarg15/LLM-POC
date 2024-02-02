"""Merge divergent branches

Revision ID: 5b72c400aed9
Revises: 11a7ff454687, a1dd8f54e5ee
Create Date: 2024-02-02 13:24:24.959930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b72c400aed9'
down_revision: Union[str, None] = ('11a7ff454687', 'a1dd8f54e5ee')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
