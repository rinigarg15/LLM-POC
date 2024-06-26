import json
from llama_index.legacy.program.openai_program import OpenAIPydanticProgram
from pydantic import BaseModel
from llama_index.legacy.llms import OpenAI

class QAPair(BaseModel):
    """A question-answer pair."""
    question: str
    answer: str

def get_assess_questions_per_node(node_text):

    prompt = """{transcript}
    --------------
    Your goal is to identify QAPairs\
    that can help a student ramp up on the topic explained in the transcript ONLY.\
    Keep the answer inside the QAPairs as descriptive as possible."""
    
    llm = OpenAI(model="gpt-3.5-turbo-0613", temperature = 0)
    program = OpenAIPydanticProgram.from_defaults(
        output_cls=QAPair,
        prompt_template_str=prompt,
        llm = llm,
    )

    response = program.stream_list(transcript=node_text)
    for r in response:
        json_data = json.dumps({"question": r.question, "answer": r.answer})
        yield json_data + "\n"