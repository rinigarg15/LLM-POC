"""Add Profile Questions

Revision ID: 4fa83b25007f
Revises: 817b38656d2e
Create Date: 2024-04-03 17:16:35.056563

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '4fa83b25007f'
down_revision: Union[str, None] = '817b38656d2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define a base class using declarative_base from SQLAlchemy
Base = declarative_base()

class ProfileQuestion(Base):
    __tablename__ = 'profile_question'
    
    id = sa.Column(sa.Integer, primary_key=True)
    text = sa.Column(sa.Text, nullable=False)
    question_type = sa.Column('question_type', sa.Enum('Text', 'Single Choice'), nullable=False)
    created_at = sa.Column(sa.DateTime, default=datetime.utcnow)
    updated_at = sa.Column(sa.DateTime, onupdate=datetime.utcnow)

def upgrade():
    # Bind the session to the Alembic operational bind
    bind = op.get_bind()
    session = Session(bind=bind)

    # Example: Inserting seed data using the ORM model
    questions = [
        ProfileQuestion(
            text="Name",
            question_type="Text",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProfileQuestion(
            text="Age",
            question_type="Text",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProfileQuestion(
            text="Gender",
            question_type="Single Choice",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProfileQuestion(
            text="Primary Language",
            question_type="Single Choice",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    ]
    
    session.add_all(questions)
    session.commit()

def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    # Example downgrade logic (if specific)
    session.query(ProfileQuestion).delete()
    session.commit()

