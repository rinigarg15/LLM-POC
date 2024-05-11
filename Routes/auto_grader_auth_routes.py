import datetime
import logging
import os
from typing import Dict, List
from grpc import Status
import jwt
from sqlalchemy import asc
from fastapi import APIRouter, Body, Cookie, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from ORM.auto_grader_orms import ProfileAnswer, ProfileQuestion, ProfileQuestionChoice, QuestionType, Role, SessionLocal, User, UserModel, UserRole

from ORM.role_constants import Roles
router = APIRouter()
logging.basicConfig(level=logging.INFO)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

@router.post('/login', response_model=UserModel)
def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    try:
        db = SessionLocal()
        user = load_user(form_data, db)

        if not user:
            raise HTTPException(status_code=400, detail="Incorrect username or password")

        if not user.check_password(form_data.password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        
        access_token = jwt.encode({"sub": form_data.username, "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}, SECRET_KEY, ALGORITHM)
        
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=False,
            max_age=3600,
            path="/",
            secure=False,   
            samesite="lax"
        )
        roles = [user_role.role.name for user_role in user.user_roles]
        profile_answer_count = db.query(ProfileAnswer).filter(ProfileAnswer.user_id == user.id).count()
        user_model = UserModel(is_logged_in=True, username=user.user_name, rolenames=roles if roles else None, profile_unfilled = profile_answer_count < 4)
        return user_model
    finally:
        db.close()

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
def check_user_exists(username: str):
    try:
        db = SessionLocal()
        user = db.query(User).filter(User.user_name == username).first()
        roles = [user_role.role.name for user_role in user.user_roles]
        profile_answer_count = db.query(ProfileAnswer).filter(ProfileAnswer.user_id == user.id).count()
        user_model = UserModel(is_logged_in=False, username=user.user_name, rolenames=roles if roles else None, profile_unfilled = profile_answer_count < 4)
        return user_model
    finally:
        db.close()
    

def current_user(token: str = Cookie(None, alias='access_token')):
    db = SessionLocal()
    credentials_exception = HTTPException(
        status_code=400,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
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

@router.post("/profile")
def create_profile(responses: List[Dict] = Body(...), user=Depends(current_user)):
    db = SessionLocal()
    for response in responses:
        profile_question_id = response["profile_question_id"]
        profile_question = db.query(ProfileQuestion).filter(ProfileQuestion.id == profile_question_id).first()
        profile_answer = db.query(ProfileAnswer).filter(ProfileAnswer.user == user, ProfileAnswer.profile_question == profile_question).first()
        if "text" in response:
            if profile_answer:
                setattr(profile_answer, "text", response["text"])
            else:
                profile_answer = ProfileAnswer(user = user, profile_question = profile_question, text = response["text"])
                db.add(profile_answer)
        else:
            if profile_answer:
                setattr(profile_answer, "profile_question_choice_id", response["profile_question_choice_id"])
            else:
                profile_answer = ProfileAnswer(user = user, profile_question = profile_question, profile_question_choice_id = response["profile_question_choice_id"])
                db.add(profile_answer)
        
    db.commit()
    db.close()
    return True

@router.get("/profile_questions")
def profile_questions(user=Depends(current_user)):
    db = SessionLocal()
    profile_questions_text = []
    profile_questions = db.query(ProfileQuestion).all()
    for profile_question in profile_questions:

        profile_answer = db.query(ProfileAnswer).filter(
            ProfileAnswer.user_id == user.id,
            ProfileAnswer.profile_question_id == profile_question.id
        ).first()
        answer = None
        if profile_question.question_type == QuestionType.SINGLE_CHOICE:
            if profile_answer:
                answer = profile_answer.profile_question_choice.id
            profile_questions_text.append({"profile_question_text" : profile_question.text, "profile_question_id":  profile_question.id, "choice_type": True, "choices" : [{"text": question_choice.text, "id":question_choice.id}for question_choice in profile_question.profile_question_choices], "answer": answer})
        else:
            if profile_answer:
                answer = profile_answer.text
            profile_questions_text.append({"profile_question_text" : profile_question.text, "profile_question_id":  profile_question.id, "choice_type": False, "answer": answer})
    db.close()
    return profile_questions_text

@router.get("/is_admin")
def is_admin(user=Depends(current_user)):
    db = SessionLocal()
    role = db.query(UserRole).filter(UserRole.user == user).first().role
    is_admin = role.name == Roles.ADMIN
    db.close()
    return is_admin

@router.get("/is_user_logged_in", response_model=UserModel)
def is_user_logged_in(user=Depends(current_user)):
    db = SessionLocal()
    db.add(user)
    db.refresh(user)
    roles = [user_role.role.name for user_role in user.user_roles]
    profile_answer_count = db.query(ProfileAnswer).filter(ProfileAnswer.user_id == user.id).count()
    user_model = UserModel(is_logged_in=True, username=user.user_name, rolenames=roles if roles else None, profile_unfilled = profile_answer_count < 4)
    db.close()
    return user_model

def create_student_user_role(new_user: User, db):
    student_role = db.query(Role).filter(Role.name == Roles.STUDENT.value).first()
    user_role = UserRole(user = new_user, role = student_role)
    db.add(user_role)

def load_user(form_data, db):
    user = db.query(User).filter(User.user_name == form_data.username).first()
    return user
