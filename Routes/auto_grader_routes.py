import io
import json
import os

from llama_index.legacy.llms import OpenAI
from sqlalchemy import asc
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
from ORM.auto_grader_orms import Board, FeedbackLength, QuestionData, QuestionDataUpdate, QuestionPaperData, Topic,UnderstandingLevel, MarkingScheme, Question, QuestionChoice, QuestionPaper, SessionLocal, Tone, User, UserQuestionAnswer, UserQuestionPaper, UserQuestionPaperData, enum_to_model
from llama_index.legacy.llms.llm import stream_completion_response_to_tokens, stream_chat_response_to_tokens
from llama_index.legacy.llms import ChatMessage
from fastapi.responses import StreamingResponse
from llama_index.legacy import ServiceContext
from llama_index.legacy.response_synthesizers.tree_summarize import TreeSummarize
from fastapi import Body
from typing import Dict
from ORM.populate_tables import State, create_ques_and_ques_choices, add_question_paper
import tiktoken
from llama_index.legacy.callbacks import CallbackManager, TokenCountingHandler
from cachetools import cached, TTLCache
from Routes.auto_grader_auth_routes import current_user
from Routes.llm_methods import assessment_llm, generate_answer_feedback, generate_next_steps, next_steps_llm

router = APIRouter()
cache = TTLCache(maxsize=100, ttl=1 * 24 * 60 * 60)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

# TEMP_DIR = "temp"
# def upload_file(file: UploadFile):
#     file_location = os.path.join(TEMP_DIR, file.filename)
#     with open(file_location, "wb+") as file_object:
#         file_object.write(file.file.read())
#     return file_location

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
# if not os.path.exists(TEMP_DIR):
#     os.makedirs(TEMP_DIR)


    
@router.get("/score")
def get_score(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper_score= db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first().score
    db.close()
    return user_question_paper_score

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

        return{"correct": True}
    else:
        correct_label = marking_scheme.question_choice.label
        db.commit()
        db.close()
        return {"correct": False, "correct_label": correct_label}
        
    
@router.get("/answer_feedback")
def get_answer_feedback(question_id: int, student_answer_choice_id: int, user_question_paper_id: int):
    db = SessionLocal()
    question = db.query(Question).filter(Question.id == question_id).first()
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question_id).first()
    correct_answer_choice = db.query(QuestionChoice).filter(QuestionChoice.id == marking_scheme.correct_question_choice_id).first().choice_text
    student_answer_choice = db.query(QuestionChoice).filter(QuestionChoice.id == student_answer_choice_id).first().choice_text
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    return generate_answer_feedback(correct_answer_choice, student_answer_choice, question, user_question_paper, db)
    
@router.post("/answer_feedback")
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

@router.get("/test_feedback")
def get_test_feedback(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()
    num_questions = db.query(Question).filter(Question.question_paper_id == user_question_paper.question_paper.id).count()
    if user_question_paper.score == num_questions:
        def iter_string():
            yield "Great job! You got all your answers correct! Keep it up!".encode('utf-8')
        db.close()
        return StreamingResponse(io.BytesIO(b"".join(iter_string())))
    else:
        return assessment_llm(user_question_paper, db)

@router.post("/test_feedback")
def post_test_feedback(user_question_paper_id: int, feedback):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()
    user_question_paper.feedback = feedback

    db.commit()
    db.close()

@router.get("/next_steps")
def get_next_steps(question_id: int, user_question_paper_id: int):
    db = SessionLocal()
    question = db.query(Question).filter(Question.id == question_id).first()
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question_id).first()
    correct_choice_text = db.query(QuestionChoice).filter(QuestionChoice.id == marking_scheme.correct_question_choice_id).first().choice_text
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    return generate_next_steps(correct_choice_text, question, user_question_paper, db)
    
@router.post("/next_steps")
def post_next_steps(question_id: int, user_question_paper_id: int, next_steps):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    user_question_answer = db.query(UserQuestionAnswer).filter(UserQuestionAnswer.question_id == question_id, UserQuestionAnswer.user_question_paper_id == user_question_paper.id).first()

    user_question_answer.next_steps = next_steps

    if user_question_paper.next_steps:
        user_question_paper.next_steps += next_steps
    else:
        user_question_paper.next_steps = next_steps

    db.commit()
    db.close()

@router.get("/test_next_steps")
def get_test_next_steps(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()
    return next_steps_llm(user_question_paper, db)

@router.post("/test_next_steps")
def post_test_next_steps(user_question_paper_id: int, next_steps):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()
    user_question_paper.next_steps = next_steps

    db.commit()
    db.close()

@router.get("/question_papers")
def question_papers(_user=Depends(current_user)):
    db = SessionLocal()
    question_papers = db.query(QuestionPaper).filter(QuestionPaper.state == State.COMPLETED.value).all()
    result = [{"name": qp.name, "id": qp.id} for qp in question_papers]
    db.close()
    return result

@router.post("/user_question_papers")
def create_user_question_paper(form_data: UserQuestionPaperData, user=Depends(current_user)):
    user_id = user.id
    db = SessionLocal()
    user_question_paper = UserQuestionPaper(user_id=user_id, question_paper_id = form_data.question_paper_id, score = 0, understanding_level = form_data.understanding_level, tone = form_data.tone, feedback_length = FeedbackLength.ELABORATE.value)
    db.add(user_question_paper)
    db.commit()
    user_question_paper_id = user_question_paper.id
    num_questions = db.query(Question).filter(Question.question_paper_id == form_data.question_paper_id).count()
    db.close()
    return {"user_question_paper_id": user_question_paper_id, "num_questions": num_questions}

@router.get("/questions/{question_paper_id}")
@cached(cache)
def get_questions_for_paper(question_paper_id: int, page_number: int = 1,  page_size: int = 1):
    offset_val = (page_number - 1) * page_size

    db = SessionLocal()
    question_list = {}
    question = db.query(Question).filter(Question.question_paper_id == question_paper_id).order_by(asc(Question.id)).limit(page_size).offset(offset_val).first()
    if question:
        question_list["text"] = question.question_text
        question_list["id"] = question.id

        question_choices = db.query(QuestionChoice).filter(QuestionChoice.question == question).all()
        question_list["choices"] = [{"text": question_choice.choice_text,"id": question_choice.id, "label": question_choice.label} for question_choice in question_choices]

    db.close()
    return question_list

@router.get("/get_questions/{question_paper_id}")
def get_questions_for_paper(question_paper_id: int):
    db = SessionLocal()
    result = []
    questions = db.query(Question).filter(Question.question_paper_id == question_paper_id).all()
    for question in questions:
        question_choices = db.query(QuestionChoice).filter(QuestionChoice.question == question).all()
        questions_list = [(question.question_text, question.id), [(question_choice.choice_text, question_choice.id, question_choice.label) for question_choice in question_choices]]
        marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question.id).first()
        if marking_scheme:
            questions_list.append(marking_scheme.question_choice.label)
        result.append(questions_list)

    db.close()
    return result

@router.get("/question/{question_id}")
def get_question(question_id: int):
    db = SessionLocal()
    result = {}

    question = db.query(Question).filter(Question.id == question_id).first()
    result["question_text"] = question.question_text

    question_choices = db.query(QuestionChoice).filter(QuestionChoice.question == question).all()
    result["question_choices"] = [{"text":question_choice.choice_text, "id": question_choice.id, "label": question_choice.label} for question_choice in question_choices]
    
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question.id).first()
    if marking_scheme:
        result["correct_choice_id"] = marking_scheme.correct_question_choice_id

    db.close()
    return result

@router.post("/question_paper")
def create_question_paper(form_data: QuestionPaperData):
    question_paper_id = add_question_paper(form_data)
    return question_paper_id

@router.post("/question")
def create_question(form_data: QuestionData):
    create_ques_and_ques_choices(form_data)

@router.get("/tests")
def list_tests(user=Depends(current_user)):
    user_id = user.id

    db = SessionLocal()
    user_question_papers = db.query(UserQuestionPaper).filter(UserQuestionPaper.user_id == user_id).all()
    result = []
    
    for user_question_paper in user_question_papers:
        num_questions = db.query(Question).filter(Question.question_paper_id == user_question_paper.question_paper.id).count()
        result.append([user_question_paper.question_paper.name, user_question_paper.score, num_questions, user_question_paper.feedback])
    db.close()
    return Response(json.dumps(result), media_type="application/json")

@router.put("/question_paper/{question_paper_id}")
def update_question_paper_state(question_paper_id: int, state: State):
    db = SessionLocal()
    question_paper = db.query(QuestionPaper).filter(QuestionPaper.id == question_paper_id).first()
    question_paper.state = state
    db.commit()
    db.close()

@router.delete("/questions/{question_id}")
def delete_question(question_id: int):
    db = SessionLocal()
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    marking_scheme = db.query(MarkingScheme).where(MarkingScheme.question_id == question.id).first()
    db.delete(marking_scheme)
    db.commit()
    db.query(QuestionChoice).where(QuestionChoice.question_id == question.id).delete()
    db.delete(question)
    db.commit()
    db.close()
    return True

@router.put("/questions/{question_id}")
def update_question(question_id: int, form_data: QuestionDataUpdate):
    db = SessionLocal()
    correct_choice_id = form_data.correct_choice_id

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.question_text != form_data.question_text:
        setattr(question, "question_text", form_data.question_text)
    
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question_id).first()
    if not marking_scheme:
        raise HTTPException(status_code=404, detail="Marking Scheme not found")
    
    for label, choice_text in form_data.choices.items():
        choice = db.query(QuestionChoice).filter(QuestionChoice.label == label, QuestionChoice.question_id == question.id).first()
        if not choice:
            raise HTTPException(status_code=404, detail=f"Choice with label {label} not found")
        if choice.choice_text != choice_text:
            setattr(choice, "choice_text", choice_text)

    if marking_scheme.correct_question_choice_id != correct_choice_id:
        setattr(marking_scheme, "correct_question_choice_id", correct_choice_id)

    db.commit()
    db.close()
    return {"detail": "Updated successfully"}

@router.get("/generate_latex")
def generate_latex(text):
    prompt = f"""
    text: {text}

    --------------------------------------------------------
    Please identify any LaTeX compatible components in the following text and convert them into their corresponding LaTeX code, enclosed in '$$'. Ensure that the original wording and structure of the text remain unchanged. Begin your response directly with the converted text, omitting any introductory phrases or explanations. The response should consist solely of the original text with the LaTeX compatible components replaced by their LaTeX code.
    """

    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.complete(prompt)
    return response

@router.get("/generate_latex_react")
def generate_latex_react(text):
    prompt = f"""
    text: {text}

    --------------------------------------------------------
    Please identify any LaTeX compatible components in the following text and convert them into their corresponding LaTeX code, enclosed in '<InlineMath>'. Also since JSX treats backslashes (\) as escape characters please use double backslashes (\\) to represent a single backslash in your LaTeX. Ensure that the original wording and structure of the text remain unchanged. Begin your response directly with the converted text, omitting any introductory phrases or explanations. The response should consist solely of the original text with the LaTeX compatible components replaced by their LaTeX code.
    """

    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.complete(prompt)
    return response

@router.get("/show_next_steps")
def show_next_steps(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper_next_steps = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first().next_steps
    db.close()

    if user_question_paper_next_steps:
        return True
    return False

@router.get("/get_qp_enums")
def get_qp_enums():
    return {"topics": enum_to_model(Topic), "boards": enum_to_model(Board)}

@router.get("/get_test_enums")
def get_test_enums():
    return {"understanding_levels": enum_to_model(UnderstandingLevel), "tones": enum_to_model(Tone)}