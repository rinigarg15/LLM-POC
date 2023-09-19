from fastapi import FastAPI
from pydantic import BaseConfig
from llama_index.retrievers import VectorIndexRetriever
from llama_index.response_synthesizers import get_response_synthesizer
from llama_index.query_engine import RetrieverQueryEngine
from assess_questions import QAPair, set_assess_questions
from assessment import generate_feedback, check_similarity
from initialize_index import initialize_index
from llama_index.chat_engine.context import ContextChatEngine
from typing import List
from flash_cards_helper import get_video_duration
import math

app = FastAPI()
BaseConfig.arbitrary_types_allowed = True


@app.get("/get_transcript_summary", response_model=None)
def get_transcript_summary(yt_video_link: str):

    index = initialize_index(yt_video_link)

    retriever = VectorIndexRetriever(
        index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize', use_async = True, streaming = True)

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )

    query_text = f"""
        You are an upbeat and friendly tutor with an encouraging tone.\
        Provide Key Insights from the context information ONLY.
        For each key insight, provide relevant summary in the form of bullet points.
        Use no more than 500 words in your summary.
    """

    response_stream  = query_engine.query(query_text)
    return response_stream


@app.get("/get_flash_cards", response_model=None)
def get_flash_cards(yt_video_link: str):
    index = initialize_index(yt_video_link)

    retriever = VectorIndexRetriever(
        index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize', use_async = True, streaming = True)

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )
    video_duration = get_video_duration(yt_video_link)
    flash_cards = math.ceil((video_duration / 60))*5

    query_text = f"""
        You are an expert in creating flash cards that will help students memorize important concepts.
        Use the concept of cloze deletion to create flash cards from the context information ONLY.\
        Each flash card will have a question and a brief answer that is not more than 5 words long. \
        Label question as 'Front:' and answer as 'Back:' in your output.
        Do not create more than {flash_cards} flash cards.
        """

    response_stream  = query_engine.query(query_text)
    return response_stream


@app.get("/get_QAKey")
def get_QAKey(yt_video_link: str) -> str:
    qa_pairs = set_assess_questions(yt_video_link)
    response = ""
    for index, qa in enumerate(qa_pairs):
        response += str(index+1) + ". " + qa.question + "\n"

    response += "Answer Key: \n"

    for index, qa in enumerate(qa_pairs):
        response += str(index+1) + ". " + qa.answer + "\n"

    return response


@app.get("/get_chat_engine", response_model=None)
def get_chat_engine(yt_video_link: str):
    index = initialize_index(yt_video_link)
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=2,
    )

    system_prompt = f""" You are a friendly and helpful mentor whose task is to \ 
        use ONLY the context information and no other sources to answer the question being asked.\
        If you don't find an answer within the context, SAY 'Sorry, I could not find the answer within the context.' \ 
        and DO NOT provide a generic response."""
    chat_engine = ContextChatEngine.from_defaults(
        verbose=True, system_prompt=system_prompt, retriever=retriever)
    return chat_engine


@app.get("/chat")
def chat(chat_engine: ContextChatEngine, query: str) -> str:
    return str(chat_engine.chat(query))


@app.get("/get_assess_questions")
def get_assess_questions(yt_video_link: str) -> List[QAPair]:
    return set_assess_questions(yt_video_link)


@app.get("/get_assessment")
def get_assessment(question: str, correct_answer: str, student_answer: str) -> str:
    similarity_score = check_similarity(correct_answer, student_answer)
    full_response = {}
    score = similarity_score * 100

    if similarity_score <= 60:
        full_response["Correct"] = "No " + "(" + str(score) + "%)"
    elif similarity_score > 60:
        if similarity_score >= 90:
            full_response["Correct"] = "Yes " + "(" + str(score) + "%)"
        else:
            full_response["Correct"] = "Partially Correct " + \
                "(" + str(score) + "%)"

        full_response["Feedback"] = str(generate_feedback(
            correct_answer, student_answer, question))
    full_response["Correct Answer"] = correct_answer
    return full_response
