"""change enum values for topic and state

Revision ID: 0406ec759c69
Revises: d4eadabdacaa
Create Date: 2024-02-01 15:14:46.719276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = '0406ec759c69'
down_revision: Union[str, None] = 'd4eadabdacaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('question_paper', 'topic',
               existing_type=mysql.ENUM('PHYSICS','MATHS','ECONOMICS','ACCOUNTING', 'IITJEE'),
               type_=sa.Enum('Physics', 'Maths', 'Economics', 'Accounting', 'IITJEE', name='topic'),
               existing_nullable=False)
    op.alter_column('question_paper', 'state',
               existing_type=mysql.ENUM('COMPLETED','DRAFTED'),
               type_=sa.Enum('Completed','Drafted', name='state'),
               existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('question_paper', 'topic',
               existing_type=sa.Enum('Physics', 'Maths', 'Economics', 'Accounting', 'IITJEE', name='topic'),
               type_=mysql.ENUM('PHYSICS','MATHS','ECONOMICS','ACCOUNTING', 'IITJEE'),
               existing_nullable=False)
    op.alter_column('question_paper', 'state',
               existing_type=sa.Enum('Completed','Drafted', name='state'),
               type_=mysql.ENUM('COMPLETED','DRAFTED'),
               existing_nullable=False)
    # ### end Alembic commands ###
