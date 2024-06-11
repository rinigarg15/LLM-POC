from fastapi import FastAPI
import os
import openai
from llama_index.legacy.llms import OpenAI
from llama_index.legacy.node_parser import SimpleNodeParser
from llama_index.legacy.text_splitter import TokenTextSplitter
from llama_index.legacy import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    set_global_service_context,
    load_index_from_storage,
)
#from llama_hub.youtube_transcript.base import YoutubeTranscriptReader
from pydantic import BaseConfig
from llama_index.legacy.retrievers import VectorIndexRetriever
from llama_index.legacy.response_synthesizers import get_response_synthesizer
from llama_index.legacy.query_engine import RetrieverQueryEngine
from assess_questions import get_assess_questions_per_node
from assessment import generate_feedback, check_similarity_cross_encoder
from llama_index.legacy.chat_engine.context import ContextChatEngine
from flash_cards import get_flash_cards_per_node
from video_helper import extract_video_id
from fastapi.responses import StreamingResponse
import math
from persistence import from_persist_path, persist_node_texts, DEFAULT_NODE_TEXT_LIST_KEY
from llama_index.legacy.llms.llm import stream_completion_response_to_tokens
from googleapiclient.discovery import build
from Routes import topic_routes, auto_grader_routes, auto_grader_auth_routes, net_app_routes

import isodate
from fastapi.middleware.cors import CORSMiddleware
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8501",
    "http://localhost:3000",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#app.include_router(topic_routes.router)
app.include_router(auto_grader_routes.router)
app.include_router(auto_grader_auth_routes.router)
app.include_router(net_app_routes.router)

BaseConfig.arbitrary_types_allowed = True
chat_engines_dict = {}

# def initialize_index(yt_video_link: str):
#     openai.api_key = os.getenv("OPENAI_API_KEY")

#     llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
#     service_context = ServiceContext.from_defaults(llm=llm)
#     set_global_service_context(service_context=service_context)

#     index_name = "index_" + extract_video_id(yt_video_link)
#     index_location = "./askify_indexes/"+index_name

#     if os.path.exists(index_location):
#         index = load_index_from_storage(
#             StorageContext.from_defaults(persist_dir=index_location), service_context=service_context
#         )
#     else:
#         loader = YoutubeTranscriptReader()
#         documents = loader.load_data(ytlinks=[yt_video_link])

#         node_parser = SimpleNodeParser(text_splitter=TokenTextSplitter())
#         nodes = node_parser.get_nodes_from_documents(documents)

#         index = VectorStoreIndex(nodes, service_context=service_context)
#         index.storage_context.persist(persist_dir=index_location)

#         persist_node_texts(yt_video_link, index)
#     return index

# def get_transcript_list(yt_video_link: str):
#     initialize_index(yt_video_link)
#     video_id = extract_video_id(yt_video_link)
#     persist_path= "./disk_data/"+video_id
#     node_texts_list = from_persist_path(persist_path)[DEFAULT_NODE_TEXT_LIST_KEY]
#     return node_texts_list

# @app.get("/get_video_duration")
# def get_video_duration(yt_video_link):
#     video_id = extract_video_id(yt_video_link)
#     youtube = build('youtube', 'v3', developerKey="AIzaSyAVDA1p-V-yiyQcAC84mdURZnd6EMFeH6k")
#     request = youtube.videos().list(part='contentDetails', id=video_id)
#     response = request.execute()

#     dur = isodate.parse_duration(response['items'][0]['contentDetails']['duration'])
#     return dur.total_seconds()

# @app.get("/get_flash_cards")
# def get_flash_cards(flash_cards: int, node_number: int, yt_video_link: str):
#     video_id = extract_video_id(yt_video_link)
#     persist_path= "./disk_data/"+video_id
#     node_text = from_persist_path(persist_path)[DEFAULT_NODE_TEXT_LIST_KEY][node_number]
#     return StreamingResponse(get_flash_cards_per_node(node_text, flash_cards), media_type="application/json")

# @app.post("/create_chat_engine", response_model=None)
# def create_chat_engine(yt_video_link: str, session_id: str):
#     index = initialize_index(yt_video_link)

#     retriever = VectorIndexRetriever(
#         index=index, 
#         similarity_top_k=2,
#     )
#     response_synthesizer = get_response_synthesizer(
#         response_mode='tree_summarize', use_async = True, streaming = True)

#     system_prompt = f""" You are a friendly and helpful mentor whose task is to \ 
#         use ONLY the context information and no other sources to answer the question being asked.\
#         If you don't find an answer within the context, SAY 'Sorry, I could not find the answer within the context.' \ 
#         and DO NOT provide a generic response."""
    
#     chat_engine = ContextChatEngine.from_defaults(system_prompt = system_prompt, retriever = retriever, response_synthesizer = response_synthesizer)
#     chat_engines_dict[session_id] = chat_engine
#     return {}

# @app.get("/chat")
# def chat(query: str, session_id: str):
#     chat_engine = chat_engines_dict[session_id]
#     response_stream = chat_engine.stream_chat(query)

#     return StreamingResponse(response_stream.response_gen)

# @app.get("/num_nodes")
# def num_nodes(yt_video_link: str):
#     node_texts_list = get_transcript_list(yt_video_link)

#     return len(node_texts_list)

# @app.get("/get_transcript")
# def get_transcript(yt_video_link: str):
#     node_texts_list = get_transcript_list(yt_video_link)

#     return node_texts_list

# @app.get("/get_QAKey")
# def get_QAKey(node_number: int, yt_video_link: str):
#     video_id = extract_video_id(yt_video_link)
#     persist_path= "./disk_data/"+video_id
#     node_text = from_persist_path(persist_path)[DEFAULT_NODE_TEXT_LIST_KEY][node_number]
#     return StreamingResponse(get_assess_questions_per_node(node_text), media_type="application/json")

# @app.get("/get_assessment")
# def get_assessment(question: str, correct_answer: str, student_answer: str):
#     similarity_score = check_similarity_cross_encoder(correct_answer, student_answer)
#     similarity_score = similarity_score * 100
#     similarity_score = round(similarity_score, 2)
#     full_response = {}

#     if similarity_score <= 60:
#         full_response["Correct"] = "No " + "(" + str(similarity_score) + "%)"
#     elif similarity_score > 60:
#         if similarity_score >= 90:
#             full_response["Correct"] = "Yes " + "(" + str(similarity_score) + "%)"
#         else:
#             full_response["Correct"] = "Partially Correct " + \
#                 "(" + str(similarity_score) + "%)"

#         full_response["Feedback"] = str(generate_feedback(
#             correct_answer, student_answer, question))
#     full_response["Correct Answer"] = correct_answer
#     return full_response

# @app.get("/get_key_idea_from_transcript")
# def get_key_idea_from_transcript(yt_video_link: str, word_limit: int):
#     index = initialize_index(yt_video_link)

#     retriever = VectorIndexRetriever(
#         index=index, similarity_top_k=len(index.docstore.docs))
#     response_synthesizer = get_response_synthesizer(
#         response_mode='tree_summarize', use_async = True, streaming = True)

#     query_engine = RetrieverQueryEngine(
#         retriever=retriever,
#         response_synthesizer=response_synthesizer,
#     )

#     query_text = f"""
#         You are an upbeat and friendly tutor with an encouraging tone.\
#         Generate one Key Idea of the context information provided.
#         Use no more than {word_limit} words for your Key Idea.
#         Highlight the important concepts in bold.
#     """

#     response_stream  = query_engine.query(query_text)
#     return StreamingResponse(response_stream.response_gen)

# @app.get("/generate_key_insight_with_summary")
# def generate_key_insight_with_summary(transcript: str, word_limit: int):
#     llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
#     key_idea_word_limit = int(0.2*word_limit)
#     elaboration_word_limit = word_limit - key_idea_word_limit
#     bullet_points = math.ceil(elaboration_word_limit/15)

#     prompt = f"""
#         context_information: {transcript}

#         You are an upbeat and friendly tutor with an encouraging tone who has been provided the context_information. \n"
#         Your goal is to generate a concise Summary in no more than {word_limit} words using ONLY the context information and no other sources.
#         Perform the following actions :-
#             1) Generate one Key Idea from the context_information ONLY in no more than {key_idea_word_limit} words.\n"
#             2) Elaborate your Key Idea in no more than {bullet_points} bullet points . \n
#             Your elaboration should not be in more than {elaboration_word_limit} words\n"
#             3) Format the key points in **bold** and *italicize* any relevant phrases \n"
#         Use the following format for your final output:
#             Key Idea: <Key Idea>
#             <elaboration>
#     """

#     response = llm.stream_complete(prompt)
#     stream_tokens = stream_completion_response_to_tokens(response)
#     return StreamingResponse(stream_tokens)

