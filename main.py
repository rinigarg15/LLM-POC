from fastapi import FastAPI
import os
import openai
import streamlit as st
from llama_index.llms import OpenAI
from llama_index.retrievers import VectorIndexRetriever
from llama_index.response_synthesizers import get_response_synthesizer
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.node_parser import SimpleNodeParser
from llama_index.chat_engine.context import ContextChatEngine
from llama_index import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    set_global_service_context,
    load_index_from_storage,
    download_loader,
)

app = FastAPI()

def initialize_index(yt_video_link: str):
    index_name = "index_"+ yt_video_link.split("?v=")[-1]
    index_location = "./askify_indexes/"+index_name

    os.environ["OPENAI_API_KEY"] = "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"
    openai.api_key = os.environ["OPENAI_API_KEY"]

    llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
    service_context = ServiceContext.from_defaults(llm=llm)
    set_global_service_context(service_context=service_context)

    if os.path.exists(index_location):
        index = load_index_from_storage(
            StorageContext.from_defaults(persist_dir=index_location), service_context=service_context
        )
    else:
        YoutubeTranscriptReader = download_loader("YoutubeTranscriptReader")

        loader = YoutubeTranscriptReader()
        documents = loader.load_data(ytlinks=[yt_video_link])

        node_parser = SimpleNodeParser()
        nodes = node_parser.get_nodes_from_documents(documents)

        index = VectorStoreIndex(nodes, service_context=service_context)

        index.storage_context.persist(persist_dir=index_location)
    return index

@app.get("/get_transcript_summary")
def get_transcript_summary(yt_video_link: str) -> str:
    index = initialize_index(yt_video_link)
    retriever = VectorIndexRetriever(index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(response_mode='tree_summarize')

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
    response = query_engine.query(query_text)
    return str(response)

@app.get("/get_flash_cards")
def get_flash_cards(yt_video_link: str) -> str:
    index = initialize_index(yt_video_link)
    retriever = VectorIndexRetriever(index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(response_mode='tree_summarize')

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )

    query_text = f"""
        You are an expert in creating flash cards that will help students memorize important concepts.
        Use the concept of cloze deletion to create 5 flash cards from the context information ONLY.\
        Each flash card will have a question and a brief answer that is not more than 5 words long. \
        """

    response = query_engine.query(query_text)
    return str(response)

@app.get("/get_QAKey")
def get_QAKey(yt_video_link: str) -> str:
    index = initialize_index(yt_video_link)
    retriever = VectorIndexRetriever(index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(response_mode='tree_summarize')

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )

    query_text = f"""
        Your goal is to identify a list of questions and answers \
        that can help a student ramp up on the topic explained in the context information ONLY\
        Use the following format to display your response :-
            1. <question_text_1>
            2. <question_text_2>
            .
            .
            .
            Answer Key:
            1. <answer_text_1>
            2. <answer_text_2>
        """
    response = query_engine.query(query_text)
    return str(response)

def chat(yt_video_link: str):
    index = initialize_index(yt_video_link)
    retriever = VectorIndexRetriever(
        index=index, 
        similarity_top_k=2,
    )

    system_prompt = f""" You are a friendly and helpful mentor whose task is to \ 
        use ONLY the context information and no other sources to answer the question being asked.\
        If you don't find an answer within the context, SAY 'Sorry, I could not find the answer within the context.' \ 
        and DO NOT provide a generic response."""
    chat_engine = ContextChatEngine.from_defaults(verbose=True, system_prompt = system_prompt, retriever = retriever)
    return chat_engine

def assess(_index):
    retriever = VectorIndexRetriever(
        index=_index, 
        similarity_top_k=2,
    )

    system_prompt = f""" You are a friendly and helpful reviewer whose goal is to review answers to the questions you generate \
        to help a student evaluate their understanding of the topic.
        Plan each step ahead of time before moving on.
        Perform the following actions: 
            1 - Introduce yourself to the students and \
                ask a meaningful question from the context information to assess the student's knowledge.
            2 - Wait for a response.
            3 - Assess the student's response in the context of the text provided only.\
                Evaluate the response on each of the [parameters] and provide a line of feedback. 
                [parameters]
                - Does the response answer all sub questions in the question?
                - Does the response answer all sub questions correctly?
                - Is the answer elaborate enough or is it in need of more explanation?
            4 - Continue these actions until the student types "Exit".
        """
    chat_engine = ContextChatEngine.from_defaults(verbose=True, system_prompt = system_prompt, retriever = retriever)
    return chat_engine

