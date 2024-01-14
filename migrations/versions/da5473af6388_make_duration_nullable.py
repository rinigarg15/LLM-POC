"""Make duration nullable

Revision ID: da5473af6388
Revises: e86f8c7d571f
Create Date: 2024-01-12 13:36:27.225120

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'da5473af6388'
down_revision: Union[str, None] = 'e86f8c7d571f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('question_paper', 'duration',
               existing_type=mysql.INTEGER(),
               nullable=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('question_paper', 'duration',
               existing_type=mysql.INTEGER(),
               nullable=False)
    # ### end Alembic commands ###
