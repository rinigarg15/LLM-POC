import io
import json
import os
from llama_index.llms import OpenAI
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from ORM.auto_grader_orms import MarkingScheme, Question, QuestionChoice, QuestionPaper, SessionLocal, User, UserQuestionAnswer, UserQuestionPaper
from llama_index.llm_predictor.utils import stream_completion_response_to_tokens
from fastapi.responses import StreamingResponse
from llama_index import ServiceContext
from llama_index.response_synthesizers.tree_summarize import TreeSummarize
from fastapi import Body
from typing import Dict
from ORM.populate_tables import State, create_ques_and_ques_choices, add_question_paper

router = APIRouter()

# SECRET_KEY = os.getenv("SECRET_KEY")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 20
# #TEMP_DIR = "temp"

# manager = LoginManager(SECRET_KEY, token_url='/login', use_cookie=False)

# if not os.path.exists(TEMP_DIR):
#     os.makedirs(TEMP_DIR)
# @router.post('/login')
# def login(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = load_user(form_data)
#     if not user:
#         raise HTTPException(status_code=400, detail="Incorrect username or password")

#     if not user.check_password(form_data.password):
#         raise HTTPException(status_code=400, detail="Incorrect username or password")
    
#     access_token = manager.create_access_token(data={'sub': form_data.username})
#     return {'access_token': access_token, 'token_type': 'bearer'}

# @router.post("/signup")
# def signup(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
#     existing_user = load_user(form_data, db)
#     if existing_user:
#         raise HTTPException(status_code=400, detail="Username already registered")

#     new_user = User(user_name=form_data.username)
#     new_user.set_password(form_data.password)
#     db.add(new_user)
#     db.commit()
#     return {"message": "User created successfully"}

# @manager.user_loader
# def load_user(form_data, db: Session = Depends(get_db)):
#     user = db.query(User).filter(User.user_name == form_data.username).first()
#     return user
# def upload_file(file: UploadFile):
#     file_location = os.path.join(TEMP_DIR, file.filename)
#     with open(file_location, "wb+") as file_object:
#         file_object.write(file.file.read())
#     return file_location

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/final_assessment")
def final_assessment(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    if user_question_paper.score >= 5:
        def iter_string():
            yield "Great job! You got all your answers correct! Keep it up!".encode('utf-8')

        return StreamingResponse(io.BytesIO(b"".join(iter_string())))
    else:
        return assessment_llm(user_question_paper)
    
@router.get("/get_score")
def get_score(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    return f"""Your score is {user_question_paper.score} / {user_question_paper.question_paper.num_questions}"""
 
def assessment_llm(user_question_paper):
    prompt = f"""
    feedback: {user_question_paper.feedback}
    topic: {user_question_paper.question_paper.topic}
    
    --------------------------------------------------------
    You are a friendly and helpful reviewer who has been given the lines\
    of feedback a student received in taking a MCQ test on the topic.
    Your job is to create a relevant and concise bulleted summary from the individual feedback\
    that can help the student hone his preparation on the given topic.
    In your feedback, enclose any mathematical equation in LaTeX, \
    using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
    Ensure that ONLY the mathematical equation is within these markers, not the entire text. \
    """

    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.stream_complete(prompt)
    stream_tokens = stream_completion_response_to_tokens(response)
    return StreamingResponse(stream_tokens)

def assessment_tree_summarise(user_question_paper):
    db = SessionLocal()
    user_question_answers= db.query(UserQuestionAnswer).filter(UserQuestionAnswer.user_question_paper_id == user_question_paper.id).all()
    topic = user_question_paper.question_paper.topic

    llm = OpenAI(model="gpt-4")
    service_context = ServiceContext.from_defaults(llm=llm)
    response_synthesizer = TreeSummarize(streaming = True, service_context=service_context)

    query_text = f"""
        You are a friendly and helpful reviewer who has been given the lines\
        of feedback a student received in taking a MCQ test on the {topic}.
        Your job is to create a relevant and concise bulleted summary from the individual feedback\
        that can help the student hone his preparation on {topic}.
        In your feedback, enclose any mathematical equation in LaTeX, \
        using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
        Ensure that ONLY the mathematical equation is within these markers, not the entire text. \
    """

    texts = []
    for answer in user_question_answers:
        if not answer.feedback:
            continue
        texts.append(answer.feedback)

    response = response_synthesizer.get_response(
        query_text,
        texts
    )
    return StreamingResponse(response)

@router.post("/check_answer")
def check_answer(question_id: int, student_answer_choice_id: int, user_question_paper_id: int):
    db = SessionLocal()
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question_id).first()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    user_question_answer = db.query(UserQuestionAnswer).filter(UserQuestionAnswer.question_id == question_id, UserQuestionAnswer.user_question_paper == user_question_paper).first()
    if not user_question_answer:
        user_question_answer = UserQuestionAnswer(question_id=question_id, user_question_paper = user_question_paper, question_choice_id = student_answer_choice_id)
        db.add(user_question_answer)
    else:
        user_question_answer.question_choice_id = student_answer_choice_id

    if marking_scheme.correct_question_choice_id == student_answer_choice_id:
        user_question_paper.score += 1
        db.commit()
        db.close()

        return Response(json.dumps({"Correct": "Yes"}), media_type="application/json")
    else:
        db.commit()
        db.close()
        return Response(json.dumps({"Correct": "No"}), media_type="application/json")
        
    
@router.post("/generate_feedback")
def generate_feedback(question_id: int, student_answer_choice_id: int):
    db = SessionLocal()
    question = db.query(Question).filter(Question.id == question_id).first()
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question_id).first()
    correct_answer_choice = db.query(QuestionChoice).filter(QuestionChoice.id == marking_scheme.correct_question_choice_id).first().choice_text
    student_answer_choice = db.query(QuestionChoice).filter(QuestionChoice.id == student_answer_choice_id).first().choice_text

    return generate_answer_feedback(correct_answer_choice, student_answer_choice, question)
    
@router.post("/post_answer_feedback")
def post_answer_feedback(question_id: int, user_question_paper_id: int, feedback):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    user_question_answer = db.query(UserQuestionAnswer).filter(UserQuestionAnswer.question_id == question_id, UserQuestionAnswer.user_question_paper_id == user_question_paper.id).first()

    user_question_answer.feedback = feedback

    if user_question_paper.feedback:
        user_question_paper.feedback += feedback
    else:
        user_question_paper.feedback = feedback

    db.commit()
    db.close()

@router.post("/post_paper_feedback")
def post_paper_feedback(user_question_paper_id: int, feedback):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()
    user_question_paper.feedback = feedback

    db.commit()
    db.close()

@router.get("/question_papers")
def question_papers():
    db = SessionLocal()
    question_papers = db.query(QuestionPaper).filter(QuestionPaper.state == State.COMPLETED.value).all()
    db.close()
    return question_papers

@router.post("/user_questions_paper")
def create_user_question_paper(question_paper_id: int):
    user_id = 1
    db = SessionLocal()
    user_question_paper = UserQuestionPaper(user_id=user_id, question_paper_id = question_paper_id, score = 0)
    db.add(user_question_paper)
    db.commit()
    user_question_paper_id = user_question_paper.id
    num_questions = user_question_paper.question_paper.num_questions
    db.close()
    return {"user_question_paper_id": user_question_paper_id, "num_questions": num_questions}

@router.get("/questions/{question_paper_id}")
def get_questions_for_paper(question_paper_id: int):
    db = SessionLocal()
    result = []
    questions = db.query(Question).filter(Question.question_paper_id == question_paper_id).all()
    for question in questions:
        question_choices = db.query(QuestionChoice).filter(QuestionChoice.question == question).all()
        marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question.id).first()
        questions_list = [(question.question_text, question.id), [(question_choice.choice_text, question_choice.id) for question_choice in question_choices]]
        if marking_scheme:
            questions_list.append(marking_scheme.correct_question_choice_id)
        result.append(questions_list)

    db.close()
    return result

@router.post("/create_question_paper")
def create_question_paper(form_data: Dict = Body(...)):
    question_paper_id = add_question_paper(form_data)
    return question_paper_id

@router.post("/create_question")
def create_question(form_data: Dict = Body(...)):
    create_ques_and_ques_choices(form_data)

@router.get("/list_tests")
def list_tests():
    user_id = 1

    db = SessionLocal()
    user_question_papers = db.query(UserQuestionPaper).filter(UserQuestionPaper.user_id == user_id).all()
    result = []
    for user_question_paper in user_question_papers:
        result.append([user_question_paper.question_paper.name, user_question_paper.score, user_question_paper.question_paper.num_questions, user_question_paper.feedback])
    db.close()
    return Response(json.dumps(result), media_type="application/json")

@router.post("/update_question_paper_state")
def update_question_paper_state(question_paper_id: int, state: State):
    db = SessionLocal()
    question_paper = db.query(QuestionPaper).filter(QuestionPaper.id == question_paper_id).first()
    question_paper.state = state
    db.commit()
    db.close()

@router.delete("/delete_questions/{question_id}")
def delete_question(question_id: int):
    db = SessionLocal()
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(question)
    db.commit()
    db.close()
    return True

# @router.post("/update_question")
# def update_question(update: UpdateModel):
#     original = update.original
#     modified = update.modified

#     # Find the database entry to update
#     db_item = db.query(YourModel).filter(YourModel.id == original["id"]).first()
#     if not db_item:
#         raise HTTPException(status_code=404, detail="Item not found")

#     # Compare and update fields if they have changed
#     for field, value in modified.items():
#         if original[field] != value:
#             setattr(db_item, field, value)

#     db.commit()
#     return {"detail": "Updated successfully"}

def generate_answer_feedback(correct_answer_text, student_answer_text, question):
    prompt = f"""
    question: {question.question_text}
    correct_answer: {correct_answer_text}
    student_answer: {student_answer_text}
    topic: {question.question_paper.topic}
    standard: {question.question_paper.standard}

    --------------------------------------------------------
    You are an upbeat and friendly tutor with an encouraging tone who has been provided the \
    correct_answer and the student_answer to a MCQ question for class standard on the given topic. \
    All the 3 fields - correct_answer, student_answer, and question are in LaTeX.
    The student_answer is wrong.
    Your goal is to generate concise feedback to help the student, \
    with the important points highlighted in bold. The feedback should be appropriate for students in class standard, \
    taking into account both the topic and their level of understanding.
    Perform the following actions:
    1) Politely inform the student of the correct_answer.
    2) Generate appropriate bulleted feedback \
    by taking into account both the topic and that the feedback is meant for class standard students,
    so that the student doesn't make the same mistake again.
    In your feedback, enclose any mathematical equation in LaTeX, \
    using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
    Ensure that ONLY the mathematical equation is within these markers, not the entire text. \
    Do not address the student by saying "Dear student".
    """

    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.stream_complete(prompt)
    stream_tokens = stream_completion_response_to_tokens(response)
    return StreamingResponse(stream_tokens)

@router.get("/generate_latex")
def generate_latex(equation):
    prompt = f"""
    equation: {equation}

    --------------------------------------------------------
    Your goal is to generate LaTex for the provided equation. \
    Enclose your generated LaTex in '$$' at the start and end for proper rendering in Streamlit\
    """

    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.complete(prompt)
    return response