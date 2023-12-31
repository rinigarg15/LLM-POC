"""add standard column to question_paper

Revision ID: 96147d6a5137
Revises: 5650c5dbe009
Create Date: 2023-12-16 13:49:40.063864

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96147d6a5137'
down_revision: Union[str, None] = '5650c5dbe009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('question_paper', sa.Column('standard', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('question_paper', 'standard')
    # ### end Alembic commands ###
