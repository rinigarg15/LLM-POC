"""add profile_question_choice table

Revision ID: 740ee4ecd1ef
Revises: 679c61c108e2
Create Date: 2024-04-01 18:16:25.931073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = '740ee4ecd1ef'
down_revision: Union[str, None] = '679c61c108e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('profile_question_choice',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('profile_question_id', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['profile_question_id'], ['profile_question.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('profile_question_choice')
    # ### end Alembic commands ###
