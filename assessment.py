from llama_index.llms import OpenAI
from llama_index.program.openai_program import OpenAIPydanticProgram
from pydantic import BaseModel


class SimilarityScore(BaseModel):
    """Get similarity score between student_answer and correct_answer"""
    score: float


class Feedback(BaseModel):
    """Generate feedback for student"""
    feedback: str


def check_similarity(correct_answer, student_answer):
    prompt = """ 
    Text1: {correct_answer}
    Text2: {student_answer}
    
    You have two texts Text1 and Text2 that you'd like to compare for their similarity. 
    Please assess the extent of matching between the two texts and provide a similarity score.
    """

    llm = OpenAI(model="gpt-3.5-turbo-0613")
    program = OpenAIPydanticProgram.from_defaults(
        output_cls=SimilarityScore,
        prompt_template_str=prompt,
        llm=llm,
    )
    response = program(correct_answer=correct_answer,
                       student_answer=student_answer)
    return response.score


def generate_feedback(correct_answer, student_answer, question):
    prompt = """
    question: {question}
    correct_answer: {correct_answer}
    student_answer: {student_answer}
    
    --------------------------------------------------------
    You are a friendly and helpful reviewer who has been the given the correct_answer\
    and the student_answer to a question.

    Perform the following actions:-
    1) Identify the missing components in the student_answer by comparing it to ONLY the correct_answer.

    2) Generate feedback to the student based on these missing components. You can use question for more context.
    """

    llm = OpenAI(model="gpt-3.5-turbo")
    program = OpenAIPydanticProgram.from_defaults(
        output_cls=Feedback,
        prompt_template_str=prompt,
        llm=llm,
    )
    response = program(correct_answer=correct_answer,
                       student_answer=student_answer, question=question)
    return str(response.feedback)
