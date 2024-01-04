from fastapi import HTTPException
from ORM.auto_grader_orms import MarkingScheme, Question, QuestionChoice, QuestionPaper, SessionLocal, State
from datetime import datetime
from typing import Dict

def add_question_paper(form_data: Dict):
    db = SessionLocal()
    question_paper = QuestionPaper(topic = form_data["topic"], num_questions = form_data["num_questions"], type = "MCQ", date = datetime.fromisoformat(form_data["date"]), duration = form_data["duration"], board = form_data["board"], name = form_data["name"], standard = form_data["standard"], state = State.DRAFTED)
    db.add(question_paper)
    db.commit()
    question_paper_id = question_paper.id
    db.close()
    return question_paper_id

def create_ques_and_ques_choices(form_data: Dict):
    db = SessionLocal()
    question_paper_id = form_data["question_paper_id"]
    question_number = db.query(Question).filter(Question.question_paper_id == question_paper_id).count() + 1
    question = Question(question_text = form_data['question_text'], question_number = question_number, question_paper_id = question_paper_id)
    db.add(question)
    db.commit()
    marking_scheme = None

    for label, choice_text_dict in form_data['choices'].items():
        question_choice = QuestionChoice(choice_text = choice_text_dict["text"], question = question, label = label)
        db.add(question_choice)
        if choice_text_dict["is_selected"]:
            marking_scheme = MarkingScheme(question=question, question_choice= question_choice, marks = 1)
            db.add(marking_scheme)
        db.commit()

    if not marking_scheme:
        db.rollback()
    db.close()
    if not marking_scheme:
        raise HTTPException(status_code=404, detail="Please provide the correct option")