"""change humourous to humorous in tone

Revision ID: 6df2add68469
Revises: a802ee6fe1ba
Create Date: 2024-01-16 17:12:00.499817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '6df2add68469'
down_revision: Union[str, None] = 'a802ee6fe1ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user_question_paper', 'tone',
               existing_type=mysql.ENUM('FORMAL', 'CASUAL', 'GENZ', 'HUMOUROUS'),
               type_=sa.Enum('FORMAL', 'CASUAL', 'GENZ', 'HUMOROUS', name='tone'),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user_question_paper', 'tone',
               existing_type=sa.Enum('FORMAL', 'CASUAL', 'GENZ', 'HUMOROUS', name='tone'),
               type_=mysql.ENUM('FORMAL', 'CASUAL', 'GENZ', 'HUMOUROUS'),
               existing_nullable=False)
    # ### end Alembic commands ###
