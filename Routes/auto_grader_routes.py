import io
import json
import os
from llama_index.llms import OpenAI
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_login import LoginManager
import tiktoken
from ORM.auto_grader_orms import UnderstandingLevel, MarkingScheme, Question, QuestionChoice, QuestionPaper, SessionLocal, Tone, User, UserQuestionAnswer, UserQuestionPaper
from llama_index.llm_predictor.utils import stream_completion_response_to_tokens
from fastapi.responses import StreamingResponse
from llama_index import ServiceContext
from llama_index.response_synthesizers.tree_summarize import TreeSummarize
from fastapi import Body
from typing import Dict
from ORM.populate_tables import State, create_ques_and_ques_choices, add_question_paper
from llama_index.callbacks import CallbackManager, TokenCountingHandler

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

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
    
@router.get("/score")
def get_score(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()
    num_questions = db.query(Question).filter(Question.question_paper_id == user_question_paper.question_paper.id).count()
    return user_question_paper.score

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
        
    
@router.get("/answer_feedback")
def get_answer_feedback(question_id: int, student_answer_choice_id: int, user_question_paper_id: int):
    db = SessionLocal()
    question = db.query(Question).filter(Question.id == question_id).first()
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question_id).first()
    correct_answer_choice = db.query(QuestionChoice).filter(QuestionChoice.id == marking_scheme.correct_question_choice_id).first().choice_text
    student_answer_choice = db.query(QuestionChoice).filter(QuestionChoice.id == student_answer_choice_id).first().choice_text
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    return generate_answer_feedback(correct_answer_choice, student_answer_choice, question, user_question_paper)
    
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

        return StreamingResponse(io.BytesIO(b"".join(iter_string())))
    else:
        return assessment_llm(user_question_paper)

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

    return generate_advanced_next_steps(correct_choice_text, question, user_question_paper.tone)
    
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
    return next_steps_llm(user_question_paper)

@router.post("/test_next_steps")
def post_test_next_steps(user_question_paper_id: int, next_steps):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()
    user_question_paper.next_steps = next_steps

    db.commit()
    db.close()

@router.get("/question_papers")
def question_papers():
    db = SessionLocal()
    question_papers = db.query(QuestionPaper).filter(QuestionPaper.state == State.COMPLETED.value).all()
    db.close()
    return question_papers

@router.post("/user_questions_paper")
def create_user_question_paper(question_paper_id: int, understanding_level: UnderstandingLevel, tone: Tone):
    user_id = 1
    db = SessionLocal()
    user_question_paper = UserQuestionPaper(user_id=user_id, question_paper_id = question_paper_id, score = 0, understanding_level = understanding_level, tone = tone)
    db.add(user_question_paper)
    db.commit()
    user_question_paper_id = user_question_paper.id
    num_questions = db.query(Question).filter(Question.question_paper_id == question_paper_id).count()
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
        questions_list = [(question.question_text, question.id), [(question_choice.choice_text, question_choice.id, question_choice.label) for question_choice in question_choices]]
        if marking_scheme:
            questions_list.append(marking_scheme.question_choice.label)
        result.append(questions_list)

    db.close()
    return result

@router.post("/question_paper")
def create_question_paper(form_data: Dict = Body(...)):
    question_paper_id = add_question_paper(form_data)
    return question_paper_id

@router.post("/question")
def create_question(form_data: Dict = Body(...)):
    create_ques_and_ques_choices(form_data)

@router.get("/tests")
def list_tests():
    user_id = 1

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
def update_question(question_id: int, form_data: Dict):
    db = SessionLocal()
    selected_option_id = form_data["selected_option"]

    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if question.question_text != form_data["question_text"]:
        setattr(question, "question_text", form_data["question_text"])
    
    marking_scheme = db.query(MarkingScheme).filter(MarkingScheme.question_id == question_id).first()
    if not marking_scheme:
        raise HTTPException(status_code=404, detail="Marking Scheme not found")
    
    for label, choice_text in form_data["choices"].items():
        choice = db.query(QuestionChoice).filter(QuestionChoice.label == label, QuestionChoice.question_id == question.id).first()
        if not choice:
            raise HTTPException(status_code=404, detail=f"Choice with label {label} not found")
        if choice.choice_text != choice_text:
            setattr(choice, "choice_text", choice_text)

    if marking_scheme.correct_question_choice_id != selected_option_id:
        setattr(marking_scheme, "correct_question_choice_id", selected_option_id)

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

@router.get("/show_next_steps")
def show_next_steps(user_question_paper_id: int):
    db = SessionLocal()
    user_question_paper = db.query(UserQuestionPaper).filter(UserQuestionPaper.id == user_question_paper_id).first()

    if user_question_paper.next_steps:
        return True
    return False

def generate_advanced_next_steps(correct_answer_text, question, tone):
    grade = {question.question_paper.grade}
    understanding_level = UnderstandingLevel.ADVANCED
    topic =  {question.question_paper.topic}
    prompt = f"""
    question: {question.question_text}
    correct_answer: {correct_answer_text}

    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been provided the \
    correct_answer to a MCQ question for class {grade} on the given {topic}. \
    The fields correct_answer and question are in LaTeX.
    The student has answered the question correctly.
    Your goal is to generate concise next steps to help a student \
    who already has an Advanced understanding of this {topic}, deepen it with
    the important points highlighted in bold. The next steps should be appropriate for students in class {grade}, \
    taking into account the {topic}.
    Perform the following actions:
    1) Generate appropriate bulleted next steps with a very {tone} style of communication\
    by taking into account both the {topic} and the fact that the next steps are meant for class {grade} students\
    with an Advanced understanding of this {topic}, with an aim to deepen their understanding on it.
    In your next steps, enclose any LaTeX compatible component in LaTeX, \
    using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    Do not address the student by saying "Dear student".
    """


    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.stream_complete(prompt)
    stream_tokens = stream_completion_response_to_tokens(response)
    return StreamingResponse(stream_tokens)

def generate_answer_feedback(correct_answer_text, student_answer_text, question, user_question_paper):
    grade =  {question.question_paper.grade}
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone

    prompt = f"""
    question: {question.question_text}
    correct_answer: {correct_answer_text}
    student_answer: {student_answer_text}
    topic: {question.question_paper.topic}

    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been provided the \
    correct_answer and the student_answer to a MCQ question for class {grade} on the given topic. \
    All the 3 fields - correct_answer, student_answer, and question are in LaTeX.
    The student_answer is wrong.
    Your goal is to generate concise feedback to help the student, \
    with the important points highlighted in bold. The feedback should be appropriate for students in class {grade}, \
    taking into account both the topic and their {understanding_level} level understanding on the topic.
    Perform the following actions:
    1) Inform the student of the correct_answer.
    2) Generate appropriate bulleted feedback with a very {tone} style of communication\
    by taking into account both the topic and that the feedback is meant for class {grade} students\
    with a {understanding_level} level understanding on the topic,
    so that the student doesn't make the same mistake again.
    Always include a "Avoid this mistake in future" section in your feedback.
    In your feedback, enclose any LaTeX compatible component in LaTeX, \
    using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    Do not address the student by saying "Dear student".
    """


    token_counter = TokenCountingHandler(tokenizer = tiktoken.encoding_for_model("gpt-4").encode)

    llm = OpenAI(model="gpt-4", temperature = 0, callback_manager = CallbackManager([token_counter]))

    token_counter.reset_counts()
    print(
    "LLM Prompt Tokens: ",
    token_counter.prompt_llm_token_count)
    
    response = llm.complete(prompt)
    print(
    "LLM Prompt Tokens: ",
    token_counter.prompt_llm_token_count,
    "\n",
    "LLM Completion Tokens: ",
    token_counter.completion_llm_token_count,
    "\n",
    "Total LLM Token Count: ",
    token_counter.total_llm_token_count,
    )
    print("--------------")
    return response

def assessment_llm(user_question_paper):
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone

    prompt = f"""
    feedback: {user_question_paper.feedback}
    topic: {user_question_paper.question_paper.topic}
    
    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been given the lines\
    of feedback a student received in taking a MCQ test on the topic.
    Your job is to create a relevant and concise bulleted summary from the individual feedback\
    that can help the student with a {understanding_level} level understanding on the topic hone his preparation.
    Articulate a generic feedback taking cues from the student's mistakes and \
    avoid mentioning individual question feedback.
    In your feedback, enclose any LaTeX compatible component in LaTeX, \
    using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    """

    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.stream_complete(prompt)
    stream_tokens = stream_completion_response_to_tokens(response)
    return StreamingResponse(stream_tokens)

def next_steps_llm(user_question_paper):
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone
    topic = {user_question_paper.question_paper.topic}

    prompt = f"""
    next_steps: {user_question_paper.next_steps}
    
    --------------------------------------------------------
    You are a tutor with a very {tone} style of communication who has been given the lines\
    of next_steps a student received in taking a MCQ test on the {topic}, to deepen his understanding on the {topic}.
    Your job is to create a relevant and concise bulleted summary from the individual next_steps\
    that can help the student with a {understanding_level} level understanding on the {topic} to hone his preparation.
    Articulate a generic summary and avoid mentioning individual question summary.
    In your summary, enclose any LaTeX compatible component in LaTeX, \
    using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
    """

    llm = OpenAI(model="gpt-4", temperature = 0)

    response = llm.stream_complete(prompt)
    stream_tokens = stream_completion_response_to_tokens(response)
    return StreamingResponse(stream_tokens)

def assessment_tree_summarise(user_question_paper):
    db = SessionLocal()
    user_question_answers= db.query(UserQuestionAnswer).filter(UserQuestionAnswer.user_question_paper_id == user_question_paper.id).all()
    topic = user_question_paper.question_paper.topic
    understanding_level = user_question_paper.understanding_level
    tone = user_question_paper.tone

    llm = OpenAI(model="gpt-4")
    service_context = ServiceContext.from_defaults(llm=llm)
    response_synthesizer = TreeSummarize(streaming = True, service_context=service_context)

    query_text = f"""
    You are a tutor with a very {tone} style of communication who has been given the lines\
    of feedback a student received in taking a MCQ test on the {topic}.
    Your job is to create a relevant and concise bulleted summary from the individual feedback\
    that can help the student with a {understanding_level} level understanding on the {topic} hone his preparation.
    Articulate a generic feedback taking cues from the student's mistakes and \
    avoid mentioning individual question feedback.
    In your feedback, enclose any LaTeX compatible component in LaTeX, \
    using '$$' at the start and end of each LaTeX equation for proper rendering in Streamlit. \
    Ensure that ONLY the LaTeX compatible component is within these markers, not the entire text. \
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