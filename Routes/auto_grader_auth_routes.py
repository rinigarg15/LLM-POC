import os
from typing import Dict, List
from grpc import Status
import jwt
from sqlalchemy import asc
from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from ORM.auto_grader_orms import ProfileAnswer, ProfileQuestion, ProfileQuestionChoice, QuestionType, Role, SessionLocal, User, UserRole

from datetime import timedelta

from ORM.role_constants import Roles
router = APIRouter()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

manager = LoginManager(SECRET_KEY, token_url='/login', algorithm=ALGORITHM, default_expiry=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), use_cookie=True)

@router.get('/login')
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = load_user(form_data, db)
    db.close()

    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    if not user.check_password(form_data.password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token = manager.create_access_token(data={'sub': form_data.username})
    manager.set_cookie(response, access_token)
    return True

@router.post("/signup")
def signup(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    existing_user = load_user(form_data, db)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = User(user_name=form_data.username)
    new_user.set_password(form_data.password)
    
    db.add(new_user)
    create_student_user_role(new_user, db)
    db.commit()
    db.close()
    return True
    
@router.get("/check_user_exists")
def check_user_exists(user_name: str):
    db = SessionLocal()
    user = db.query(User).filter(User.user_name == user_name).first()
    db.close()
    return user is not None

def current_user(token: str = Cookie(None)):
    db = SessionLocal()
    credentials_exception = HTTPException(
        status_code=400,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        print(token)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_name = payload.get("sub")
        if user_name is None:
            raise credentials_exception
        user = db.query(User).filter(User.user_name == user_name).first()
        if user is None:
            raise credentials_exception
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please Login again.", headers={"WWW-Authenticate": "Bearer"})
    except jwt.PyJWTError:
        raise credentials_exception
    finally:
        db.close()

@router.get("/profile_unfilled")
def profile_unfilled(user=Depends(current_user)):
    db = SessionLocal()
    profile_answer_count = db.query(ProfileAnswer).filter(ProfileAnswer.user_id == user.id).count()
    db.close()
    return profile_answer_count < 4

@router.post("/reset_password")
def reset_password(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    user = load_user(form_data, db)
    user.set_password(form_data.password)
    db.commit()
    db.close()
    return True

@router.get("/profile")
def get_profile_data(user=Depends(current_user)):
    db = SessionLocal()
    profile_answers = db.query(ProfileAnswer).filter(ProfileAnswer.user == user).all()
    profile_data = []
    for profile_answer in profile_answers:
        profile_question = profile_answer.profile_question
        question_type = profile_question.question_type
        if question_type == QuestionType.TEXT:
            profile_data.append({"profile_question_text": profile_question.text, "profile_answer_text": profile_answer.text})
        else:
            profile_data.append({"profile_question_text": profile_question.text, "profile_answer_text": profile_answer.profile_question_choice.text})
    db.close()
    return profile_data

@router.post("/profile")
def create_profile(responses: List = Body(...), user=Depends(current_user)):
    db = SessionLocal()
    for response in responses:
        profile_question_id = response["profile_question_id"]
        profile_question = db.query(ProfileQuestion).filter(ProfileQuestion.id == profile_question_id).first()
        if "text" in response:
            profile_answer = ProfileAnswer(user = user, profile_question = profile_question, text = response["text"])
        else:
            selected_choice_id = response["profile_question_choice_id"]
            profile_question_choice = db.query(ProfileQuestionChoice).filter(ProfileQuestionChoice.id == selected_choice_id).first()
            profile_answer = ProfileAnswer(user = user, profile_question = profile_question, profile_question_choice = profile_question_choice)
        db.add(profile_answer)
    db.commit()
    db.close()
    return True

@router.get("/profile_questions")
def profile_questions():
    db = SessionLocal()
    profile_questions_text = []
    profile_questions = db.query(ProfileQuestion).all()
    for profile_question in profile_questions:
        if profile_question.question_type == QuestionType.SINGLE_CHOICE:
            profile_questions_text.append({"profile_question_text" : profile_question.text, "profile_question_id":  profile_question.id, "choice_type": True, "choices" : [(question_choice.text, question_choice.id) for question_choice in profile_question.profile_question_choices] })
        else:
            profile_questions_text.append({"profile_question_text" : profile_question.text, "profile_question_id":  profile_question.id, "choice_type": False})
    db.close()
    return profile_questions_text

@router.get("/is_admin")
def is_admin(user=Depends(current_user)):
    db = SessionLocal()
    role = db.query(UserRole).filter(UserRole.user == user).first().role
    is_admin = role.name == Roles.ADMIN
    db.close()
    return is_admin

@router.get("/is_user_logged_in")
def is_user_logged_in(_user=Depends(current_user)):
    return True

def create_student_user_role(new_user: User, db):
    student_role = db.query(Role).filter(Role.name == Roles.STUDENT.value).first()
    user_role = UserRole(user = new_user, role = student_role)
    db.add(user_role)

def load_user(form_data, db):
    user = db.query(User).filter(User.user_name == form_data.username).first()
    return user
