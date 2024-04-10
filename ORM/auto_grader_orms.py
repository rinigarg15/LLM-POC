from sqlalchemy.types import Enum as SQLAlchemyEnum
from enum import Enum as PyEnum
from sqlalchemy import Boolean, Text, create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, backref
from datetime import datetime
import bcrypt
import os

pwd = os.getenv('SQL_DB_PWD')
db_ip = os.getenv('DB_IP')
u_name = os.getenv('DB_USERNAME')

engine = create_engine(f'mysql+pymysql://{u_name}:{pwd}@{db_ip}:3306/auto_grader_db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class State(PyEnum):
    COMPLETED = "Completed"
    DRAFTED = "Drafted"

class UnderstandingLevel(PyEnum):
    BEGINNER = "Beginner"
    ADVANCED = "Advanced"

class Topic(PyEnum):
    PHYSICS = "Physics"
    MATHS = "Maths"
    ECONOMICS = "Economics"
    ACCOUNTING = "Accounting"
    IITJEE = "IITJEE"

class Board(PyEnum):
    IGCSE = "IGCSE"
    ICSE = "ICSE"
    CBSE = "CBSE"
    IB = "International"

class Tone(PyEnum):
    FORMAL = "Formal"
    CASUAL = "Casual"
    GENZ = "Gen-Z"
    HUMOROUS = "Humorous"

class FeedbackLength(PyEnum):
    ELABORATE = "Elaborate"
    CONCISE = "Concise"
    NO = "No"

class QuestionType(PyEnum):
    TEXT = "Text"
    SINGLE_CHOICE = "Single Choice"

class Gender(PyEnum):
    MALE = "Male"
    FEMALE = "Female"
    OTHERS = "Others"

class Language(PyEnum):
    ENGLISH = "English"
    HINDI = "Hindi"
    KANNADA = "Kannada"


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    user_name = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    def set_password(self, raw_password):
        self.password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())

    def check_password(self, raw_password):
        return bcrypt.checkpw(raw_password.encode('utf-8'), self.password.encode('utf-8'))


class QuestionPaper(Base):
    __tablename__ = 'question_paper'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    topic = Column(SQLAlchemyEnum(Topic, values_callable=lambda enum_class: [e.value for e in enum_class]), nullable=False)
    type = Column(String(100), nullable=False)
    instructions = Column(Text)
    information = Column(Text)
    date = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=True)
    board = Column(SQLAlchemyEnum(Board, values_callable=lambda enum_class: [e.value for e in enum_class]), nullable=False)
    grade = Column(Integer, nullable=True)
    state = Column(SQLAlchemyEnum(State, values_callable=lambda enum_class: [e.value for e in enum_class]), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Question(Base):
    __tablename__ = 'question'
    id = Column(Integer, primary_key=True)
    question_paper_id = Column(Integer, ForeignKey('question_paper.id'))
    question_number = Column(Integer)
    question_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationship
    question_paper = relationship("QuestionPaper", backref=backref("questions", cascade="all, delete-orphan"))

class QuestionChoice(Base):
    __tablename__ = 'question_choice'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    choice_text = Column(String(150), nullable=False)
    label = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationship
    question = relationship("Question", backref=backref("question_choices", cascade="all, delete-orphan"))

class UserQuestionPaper(Base):
    __tablename__ = 'user_question_paper'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    question_paper_id = Column(Integer, ForeignKey('question_paper.id'), nullable=False)
    score = Column(Integer, nullable=False)
    feedback = Column(Text)
    next_steps = Column(Text)
    tone = Column(SQLAlchemyEnum(Tone, values_callable=lambda enum_class: [e.value for e in enum_class]), nullable=False)
    understanding_level = Column(SQLAlchemyEnum(UnderstandingLevel, values_callable=lambda enum_class: [e.value for e in enum_class]), nullable=False)
    feedback_length = Column(SQLAlchemyEnum(FeedbackLength, values_callable=lambda enum_class: [e.value for e in enum_class]), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", backref=backref("user_question_papers", cascade="all, delete-orphan"))
    question_paper = relationship("QuestionPaper", backref=backref("user_question_papers", cascade="all, delete-orphan"))

class UserQuestionAnswer(Base):
    __tablename__ = 'user_question_answer'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    user_question_paper_id = Column(Integer, ForeignKey('user_question_paper.id'), nullable=False)
    question_choice_id = Column(Integer, ForeignKey('question_choice.id'), nullable=False)
    feedback = Column(Text)
    next_steps = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    question = relationship("Question", backref=backref("user_question_answers", cascade="all, delete-orphan"))
    user_question_paper = relationship("UserQuestionPaper", backref=backref("user_question_answers", cascade="all, delete-orphan"))
    question_choice = relationship("QuestionChoice", backref=backref("user_question_answers", cascade="all, delete-orphan"))

class MarkingScheme(Base):
    __tablename__ = 'marking_scheme'
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('question.id'), nullable=False)
    correct_question_choice_id = Column(Integer, ForeignKey('question_choice.id'), nullable=False)
    marks = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    question = relationship("Question")
    question_choice = relationship("QuestionChoice")

class ProfileQuestion(Base):
    __tablename__ = 'profile_question'
    id = Column(Integer, primary_key=True)
    text = Column(Text, nullable=False)
    question_type = Column(SQLAlchemyEnum(QuestionType, values_callable=lambda enum_class: [e.value for e in enum_class]), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class ProfileQuestionChoice(Base):
    __tablename__ = 'profile_question_choice'
    id = Column(Integer, primary_key=True)
    profile_question_id = Column(Integer, ForeignKey('profile_question.id'), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationship
    profile_question = relationship("ProfileQuestion", backref=backref("profile_question_choices", cascade="all, delete-orphan"))

class ProfileAnswer(Base):
    __tablename__ = 'profile_answer'
    id = Column(Integer, primary_key=True)
    profile_question_id = Column(Integer, ForeignKey('profile_question.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    profile_question_choice_id = Column(Integer, ForeignKey('profile_question_choice.id'))
    text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    profile_question = relationship("ProfileQuestion", backref=backref("profile_answers", cascade="all, delete-orphan"))
    profile_question_choice = relationship("ProfileQuestionChoice", backref=backref("profile_answers", cascade="all, delete-orphan"))
    user = relationship("User", backref=backref("profile_answers", cascade="all, delete-orphan"))

class Role(Base):
    __tablename__ = 'role'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class Permission(Base):
    __tablename__ = 'permission'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

class RolePermission(Base):
    __tablename__ = 'role_permission'
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('role.id'), nullable=False)
    permission_id = Column(Integer, ForeignKey('permission.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    role = relationship("Role", backref=backref("role_permissions", cascade="all, delete-orphan"))
    permission = relationship("Permission", backref=backref("role_permissions", cascade="all, delete-orphan"))

class UserRole(Base):
    __tablename__ = 'user_role'
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey('role.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    
    # Relationships
    role = relationship("Role", backref=backref("user_roles", cascade="all, delete-orphan"))
    user = relationship("User", backref=backref("user_roles", cascade="all, delete-orphan"))