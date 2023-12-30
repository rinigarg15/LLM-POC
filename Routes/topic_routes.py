from typing import Optional
from fastapi.responses import StreamingResponse
from Topics.RAG import create_RAG_topic, create_chat_engine_topic, get_stored_QAKey, get_stored_flash_cards_generator, get_stored_QAKey_generator, get_stored_key_idea_generator, get_stored_summary_generator
import nltk
from generic_helper import Topics
from fastapi import APIRouter
chat_engines_dict_topic = {}

router = APIRouter()

#@router.on_event("startup")
#def startup_event():
    #nltk.download('punkt', quiet=True, raise_on_error=False)
    #create_RAG_topic()

@router.get("/get_topic_flash_cards")
def get_topic_flash_cards(topic: Topics):
    return StreamingResponse(get_stored_flash_cards_generator(), media_type="application/json")

@router.get("/get_topic_QAKey_streamed")
def get_topic_QAKey_streamed(topic: Topics):
    return StreamingResponse(get_stored_QAKey_generator(), media_type="application/json")

@router.get("/get_topic_QAKey")
def get_topic_QAKey(topic: Topics):
    return get_stored_QAKey()

@router.get("/create_chat_engines_topic")
def create_chat_engines_topic(session_id: str):
    chat_engines_dict_topic[session_id][Topics.RAG.value] = create_chat_engine_topic()

@router.get("/chat_topic")
def chat_topic(query: str, session_id: str, topic: str):
    chat_engine = chat_engines_dict_topic[session_id][topic]
    response_stream = chat_engine.stream_chat(query)

    return StreamingResponse(response_stream.response_gen)

@router.get("/get_key_idea_from_topic")
def get_key_idea_from_topic(topic: Topics, word_limit: int):
    return StreamingResponse(get_stored_key_idea_generator())

@router.get("/get_summary_from_topic")
def get_summary_from_topic(topic: Topics, word_limit: Optional[int]):  
    return StreamingResponse(get_stored_summary_generator())    