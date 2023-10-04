from collections import defaultdict
import threading
from fastapi import FastAPI
import os
import openai
from llama_index.llms import OpenAI
from llama_index.node_parser import SimpleNodeParser
from llama_index.text_splitter import TokenTextSplitter
from llama_index import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    set_global_service_context,
    load_index_from_storage,
)
from llama_hub.youtube_transcript.base import YoutubeTranscriptReader
from pydantic import BaseConfig
from llama_index.retrievers import VectorIndexRetriever
from llama_index.response_synthesizers import get_response_synthesizer
from llama_index.query_engine import RetrieverQueryEngine
from assess_questions import get_assess_questions_per_node
from assessment import generate_feedback, check_similarity
from llama_index.chat_engine.context import ContextChatEngine
from flash_cards_helper import extract_video_id, get_video_duration
from fastapi.responses import StreamingResponse
import math
from persistence import from_persist_path, persist_node_texts, DEFAULT_NODE_TEXT_LIST_KEY
from llama_index.llm_predictor.utils import stream_completion_response_to_tokens

app = FastAPI()
BaseConfig.arbitrary_types_allowed = True
chat_engines_dict = {}

def initialize_index(yt_video_link: str):
    openai.api_key = os.getenv("OPENAI_API_KEY")

    llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
    service_context = ServiceContext.from_defaults(llm=llm)
    set_global_service_context(service_context=service_context)

    index_name = "index_" + extract_video_id(yt_video_link)
    index_location = "./askify_indexes/"+index_name

    if os.path.exists(index_location):
        index = load_index_from_storage(
            StorageContext.from_defaults(persist_dir=index_location), service_context=service_context
        )
    else:
        loader = YoutubeTranscriptReader()
        documents = loader.load_data(ytlinks=[yt_video_link])

        node_parser = SimpleNodeParser(text_splitter=TokenTextSplitter())
        nodes = node_parser.get_nodes_from_documents(documents)

        index = VectorStoreIndex(nodes, service_context=service_context)
        index.storage_context.persist(persist_dir=index_location)

        persist_node_texts(yt_video_link, index)
    return index

@app.get("/get_transcript_summary")
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
    return StreamingResponse(response_stream.response_gen)


@app.get("/get_flash_cards")
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
    return StreamingResponse(response_stream.response_gen)

@app.post("/create_chat_engine", response_model=None)
def create_chat_engine(yt_video_link: str, session_id: str):
    index = initialize_index(yt_video_link)

    retriever = VectorIndexRetriever(
        index=index, 
        similarity_top_k=2,
    )
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize', use_async = True, streaming = True)

    system_prompt = f""" You are a friendly and helpful mentor whose task is to \ 
        use ONLY the context information and no other sources to answer the question being asked.\
        If you don't find an answer within the context, SAY 'Sorry, I could not find the answer within the context.' \ 
        and DO NOT provide a generic response."""
    
    chat_engine = ContextChatEngine.from_defaults(system_prompt = system_prompt, retriever = retriever, response_synthesizer = response_synthesizer)
    global chat_engines_dict
    chat_engines_dict[session_id] = chat_engine

@app.get("/chat")
def chat(query: str, session_id: str):
    global chat_engines_dict
    chat_engine = chat_engines_dict[session_id]
    response_stream = chat_engine.stream_chat(query)

    return StreamingResponse(response_stream.response_gen)

@app.get("/num_nodes")
def num_nodes(yt_video_link: str):
    initialize_index(yt_video_link)
    node_texts_list = from_persist_path(yt_video_link)[DEFAULT_NODE_TEXT_LIST_KEY]

    return len(node_texts_list)

@app.get("/get_QAKey")
def get_QAKey(node_number: int, yt_video_link: str):
    node_text = from_persist_path(yt_video_link)[DEFAULT_NODE_TEXT_LIST_KEY][node_number]
    return StreamingResponse(get_assess_questions_per_node(node_text), media_type="application/json")

@app.get("/get_assessment")
def get_assessment(question: str, correct_answer: str, student_answer: str):
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

@app.get("/get_key_ideas_from_transcript")
def get_key_ideas_from_transcript(yt_video_link: str):
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
        Generate one Key Idea of the context information provided.
        Use no more than 50 words for your Key Idea.
    """

    response_stream  = query_engine.query(query_text)
    return StreamingResponse(response_stream.response_gen)

@app.get("/generate_key_insight_with_summary")
def generate_key_insight_with_summary(transcript: str):
    llm = OpenAI(model="gpt-3.5-turbo", temperature=0) 
    
    prompt = f"""
    " You are an upbeat and friendly tutor with an encouraging tone who has been provided context information below. \n"
    "---------------------\n"
    "{transcript}"
    "\n---------------------\n"
    "Using ONLY the context information and no other sources, perform the following actions:\n"
    "First, generate one Key Idea from the context information ONLY.\n"
    "Then elaborate your Key Idea in bullet points.\n"
    "Do not generate more than 5 bullet points.\n"
    """

    response = llm.stream_complete(prompt)
    stream_tokens = stream_completion_response_to_tokens(response)
    return StreamingResponse(stream_tokens)
