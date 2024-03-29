"""Add tone and understanding_level in user_question_paper

Revision ID: c91beac59f03
Revises: 1a24e25039d7
Create Date: 2024-01-12 15:36:01.460235

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c91beac59f03'
down_revision: Union[str, None] = '1a24e25039d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_question_paper', sa.Column('tone', sa.Enum('FORMAL', 'CASUAL', 'GENZ', 'HUMOUROUS', name='tone'), nullable=False))
    op.add_column('user_question_paper', sa.Column('understanding_level', sa.Enum('BEGINNER', 'ADVANCED', name='understandinglevel'), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user_question_paper', 'understanding_level')
    op.drop_column('user_question_paper', 'tone')
    # ### end Alembic commands ###
