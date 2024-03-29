"""Add next_steps in user_question_paper

Revision ID: 54a3b001eeb4
Revises: da5473af6388
Create Date: 2024-01-12 13:40:01.843468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54a3b001eeb4'
down_revision: Union[str, None] = 'da5473af6388'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_question_paper', sa.Column('next_steps', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_question_paper', 'next_steps')
    # ### end Alembic commands ###
