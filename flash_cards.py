import json
from llama_index.legacy.program.openai_program import OpenAIPydanticProgram
from pydantic import BaseModel
from llama_index.legacy.llms import OpenAI

class FlashCard(BaseModel):
    """A Flash-Card."""
    front: str
    back: str

def get_flash_cards_per_node(node_text, flash_cards):

    prompt = """{transcript}
    --------------
    Your goal is to identify FlashCards that can help students memorize important concepts from the transcript ONLY.
    Use the concept of cloze deletion to create your FlashCards. \
    Each flash card will have a question and a brief answer that is not more than 5 words long. 
    Do not create more than {flash_cards} FlashCards.
    """
    
    llm = OpenAI(model="gpt-3.5-turbo-0613", temperature = 0)
    program = OpenAIPydanticProgram.from_defaults(
        output_cls=FlashCard,
        prompt_template_str=prompt,
        llm = llm,
    )

    response = program.stream_list(transcript=node_text, flash_cards=flash_cards)
    for r in response:
        json_data = json.dumps({"front": r.front, "back": r.back})
        yield json_data + "\n"