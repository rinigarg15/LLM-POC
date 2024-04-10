"""Adjust enum values for topic column

Revision ID: 1cc178cce995
Revises: 243641094881
Create Date: 2024-04-03 11:47:57.979322

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql



# revision identifiers, used by Alembic.
revision: str = '1cc178cce995'
down_revision: Union[str, None] = '243641094881'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('question_paper', 'topic',
                existing_type=mysql.ENUM('PHYSICS','MATHS','ECONOMICS','ACCOUNTING', 'IITJEE'),
                type_=sa.Enum('Physics', 'Maths', 'Economics', 'Accounting', 'IITJEE', name='topic'),
                existing_nullable=False)


def downgrade() -> None:
    op.alter_column('question_paper', 'topic',
               existing_type=sa.Enum('Physics', 'Maths', 'Economics', 'Accounting', 'IITJEE', name='topic'),
               type_=mysql.ENUM('PHYSICS','MATHS','ECONOMICS','ACCOUNTING', 'IITJEE'),
               existing_nullable=False)
