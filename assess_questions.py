from initialize_index import initialize_index
from llama_index.program.openai_program import OpenAIPydanticProgram
from pydantic import BaseModel
from typing import List
from llama_index.llms import OpenAI


class QAPair(BaseModel):
    """A question-answer pair."""
    question: str
    answer: str


class QAList(BaseModel):
    """A list of QAPairs."""
    questions_answers_list: List[QAPair]


def set_assess_questions(yt_video_link):
    index = initialize_index(yt_video_link)

    prompt = """{transcript}
    --------------
    Your goal is to identify a QAList of QAPairs\
    that can help a student ramp up on the topic explained in the transcript ONLY.\
    Keep the answer inside the QAPairs as descriptive as possible."""

    llm = OpenAI(model="gpt-3.5-turbo-0613")
    program = OpenAIPydanticProgram.from_defaults(
        output_cls=QAList,
        prompt_template_str=prompt,
        llm=llm,
    )
    nodes = index.docstore.docs

    total_list = []
    for key, node in nodes.items():
        try:
            response = program(transcript=node.text)
            total_list.extend(response.questions_answers_list)
        except:
            print("Failed to parse questions from node at index ", key)
    return total_list
