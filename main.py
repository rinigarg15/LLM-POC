import threading
from typing import Optional
from fastapi import FastAPI, Depends
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
from assessment import generate_feedback, check_similarity_embedding
from llama_index.chat_engine.context import ContextChatEngine
from flash_cards import get_flash_cards_per_node
from video_helper import extract_video_id
from fastapi.responses import StreamingResponse
import math
from persistence import from_persist_path, persist_node_texts, DEFAULT_NODE_TEXT_LIST_KEY
from llama_index.llm_predictor.utils import stream_completion_response_to_tokens
from googleapiclient.discovery import build
import isodate

app = FastAPI()
BaseConfig.arbitrary_types_allowed = True

class ChatEnginesDict:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatEnginesDict, cls).__new__(cls)
            cls._instance.chat_engines_dict = {}
        return cls._instance

    def add(self, session_id, context_chat_engine):
        self.chat_engines_dict[session_id] = context_chat_engine

chat_engines_dict_object = ChatEnginesDict()

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

def get_transcript_list(yt_video_link: str):
    initialize_index(yt_video_link)
    node_texts_list = from_persist_path(yt_video_link)[DEFAULT_NODE_TEXT_LIST_KEY]
    return node_texts_list

@app.get("/get_transcript_summary")
def get_transcript_summary(yt_video_link: str, word_limit: Optional[int]):        
    index = initialize_index(yt_video_link)

    retriever = VectorIndexRetriever(
        index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize', use_async = True, streaming = True)

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )

    word_limit = word_limit or 500

    query_text = f"""
        You are an upbeat and friendly tutor with an encouraging tone.\
        Provide Key Insights from the context information ONLY.
        For each key insight, provide relevant summary in the form of bullet points.
        Use no more than {word_limit} words in your summary.
        Highlight the important words in your summary in bold.
    """

    response_stream  = query_engine.query(query_text)
    return StreamingResponse(response_stream.response_gen)

@app.get("/get_video_duration")
def get_video_duration(yt_video_link):
    video_id = extract_video_id(yt_video_link)
    youtube = build('youtube', 'v3', developerKey="AIzaSyAVDA1p-V-yiyQcAC84mdURZnd6EMFeH6k")
    request = youtube.videos().list(part='contentDetails', id=video_id)
    response = request.execute()

    dur = isodate.parse_duration(response['items'][0]['contentDetails']['duration'])
    return dur.total_seconds()

@app.get("/get_flash_cards")
def get_flash_cards(flash_cards: int, node_number: int, yt_video_link: str):
    node_text = from_persist_path(yt_video_link)[DEFAULT_NODE_TEXT_LIST_KEY][node_number]
    return StreamingResponse(get_flash_cards_per_node(node_text, flash_cards), media_type="application/json")

@app.post("/create_chat_engine", response_model=None)
def create_chat_engine(yt_video_link: str, session_id: str, chat_engines_dict_object : ChatEnginesDict = Depends()):
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
    chat_engines_dict_object.add(session_id, chat_engine)
    return {}

@app.get("/chat")
def chat(query: str, session_id: str, chat_engines_dict_object : ChatEnginesDict = Depends()):
    chat_engine = chat_engines_dict_object.chat_engines_dict[session_id]
    response_stream = chat_engine.stream_chat(query)

    return StreamingResponse(response_stream.response_gen)

@app.get("/num_nodes")
def num_nodes(yt_video_link: str):
    node_texts_list = get_transcript_list(yt_video_link)

    return len(node_texts_list)

@app.get("/get_transcript")
def get_transcript(yt_video_link: str):
    node_texts_list = get_transcript_list(yt_video_link)

    return node_texts_list

@app.get("/get_QAKey")
def get_QAKey(node_number: int, yt_video_link: str):
    node_text = from_persist_path(yt_video_link)[DEFAULT_NODE_TEXT_LIST_KEY][node_number]
    return StreamingResponse(get_assess_questions_per_node(node_text), media_type="application/json")

@app.get("/get_assessment")
def get_assessment(question: str, correct_answer: str, student_answer: str):
    similarity_score = check_similarity_embedding(correct_answer, student_answer)
    similarity_score = round(similarity_score, 2)
    full_response = {}
    score = similarity_score * 100

    if score <= 60:
        full_response["Correct"] = "No " + "(" + str(score) + "%)"
    elif score > 60:
        if score >= 90:
            full_response["Correct"] = "Yes " + "(" + str(score) + "%)"
        else:
            full_response["Correct"] = "Partially Correct " + \
                "(" + str(score) + "%)"

        full_response["Feedback"] = str(generate_feedback(
            correct_answer, student_answer, question))
    full_response["Correct Answer"] = correct_answer
    return full_response

@app.get("/get_key_ideas_from_transcript")
def get_key_ideas_from_transcript(yt_video_link: str, word_limit: int):
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
        Use no more than {word_limit} words for your Key Idea.
        Highlight the important concepts in bold.
    """

    response_stream  = query_engine.query(query_text)
    return StreamingResponse(response_stream.response_gen)

@app.get("/generate_key_insight_with_summary")
def generate_key_insight_with_summary(transcript: str, word_limit: int):
    llm = OpenAI(model="gpt-3.5-turbo", temperature=0) 
    
    prompt = f"""
    " You are an upbeat and friendly tutor with an encouraging tone who has been provided context information below. \n"
    "---------------------\n"
    "{transcript}"
    "\n---------------------\n"
    "Using ONLY the context information and no other sources, perform the following actions:\n"
    "First, generate one Key Idea from the context information ONLY.\n"
    "Then elaborate your Key Idea in bullet points.\n"
    "Do not generate more than 5 bullet points. \n"
    "Do not generate more than {word_limit} words.\n"
    "Highlight the important concepts in bold. \n"
    """

    response = llm.stream_complete(prompt)
    stream_tokens = stream_completion_response_to_tokens(response)
    return StreamingResponse(stream_tokens)
