"""Add Profile Question Choices

Revision ID: 0f6b5f48dfeb
Revises: 4fa83b25007f
Create Date: 2024-04-03 17:48:25.326422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from datetime import datetime
from sqlalchemy.sql import text

from ORM.auto_grader_orms import Gender, Language, ProfileQuestionChoice


# revision identifiers, used by Alembic.
revision: str = '0f6b5f48dfeb'
down_revision: Union[str, None] = '4fa83b25007f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


Base = declarative_base()

def upgrade():
    # Bind the session to the Alembic operational bind
    bind = op.get_bind()
    session = Session(bind=bind)

    gender_question_id = session.execute(
        text("SELECT id FROM profile_question WHERE text = 'Gender'")).scalar()
    
    language_question_id = session.execute(
        text("SELECT id FROM profile_question WHERE text = 'Primary Language'")).scalar()
    
    question_choices = []
    if gender_question_id:
        question_choices.extend([
        ProfileQuestionChoice(
            text=Gender.MALE.value,
            profile_question_id=gender_question_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProfileQuestionChoice(
            text=Gender.FEMALE.value,
            profile_question_id=gender_question_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProfileQuestionChoice(
            text=Gender.OTHERS.value,
            profile_question_id=gender_question_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )])
    
    if language_question_id:
        question_choices.extend([
        ProfileQuestionChoice(
            text=Language.ENGLISH.value,
            profile_question_id=language_question_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProfileQuestionChoice(
            text=Language.HINDI.value,
            profile_question_id=language_question_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        ),
        ProfileQuestionChoice(
            text=Language.KANNADA.value,
            profile_question_id=language_question_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )])
    
    session.add_all(question_choices)
    session.commit()

def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    # Example downgrade logic (if specific)
    session.query(ProfileQuestionChoice).delete()
    session.commit()

