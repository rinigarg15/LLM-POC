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
from llama_index.agent import OpenAIAgent
from llama_index.tools import FunctionTool, QueryEngineTool
from llama_index.tools.types import ToolMetadata
from pydantic import BaseModel

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
    openai.api_key = os.getenv("OPENAI_API_KEY")

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

class contextChatEngine(BaseModel):
    chat_engine = ContextChatEngine

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
    contextChatEngineObject = contextChatEngine()
    contextChatEngineObject.chat_engine = ContextChatEngine.from_defaults(verbose=True, system_prompt = system_prompt, retriever = retriever)
    return contextChatEngineObject

@app.get("/chat")
def chat(context_chat_engine: contextChatEngine, query: str) -> str:
    return str(context_chat_engine.chat_engine.chat(query))

assess_questions = []

def get_assess_questions(yt_video_link: str) -> None:
    global assess_questions
    index = initialize_index(yt_video_link)
    retriever = VectorIndexRetriever(index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(response_mode='tree_summarize')
    questions_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )
    query_text = f"""
        Your goal is to identify a list of questions \
        that can help a student ramp up on the topic explained in the context information ONLY\
        Provide them in the form of a python list object.
        """
    query_response = questions_engine.query(query_text)
    assess_questions = query_response.response.split(",")[::-1]

def get_assess_question() -> str:
    """Return the next question to ask the student"""
    if assess_questions:
        return assess_questions.pop()
    else:
        return "No more Questions left to ask. You can type 'exit' in the chatbox"
    
class openAIAgent(BaseModel):
    openAI_Agent = OpenAIAgent

@app.get("/get_assessment_agent", response_model=None)
def get_openAIAgent(yt_video_link: str):
    get_assess_questions(yt_video_link)
    assess_question_tool = FunctionTool.from_defaults(fn=get_assess_question)

    index = initialize_index(yt_video_link)
    llm = OpenAI(model="gpt-3.5-turbo-0613")
    retriever = VectorIndexRetriever(
        index=index, 
        similarity_top_k=2,
    )
    response_synthesizer = get_response_synthesizer(
        response_mode="compact")
    answers_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
    )
    generate_answer_tool = QueryEngineTool(
        query_engine=answers_engine,
        metadata=ToolMetadata(
            name="generate_answer_tool",
            description="Contains transcript of the youtube video with the link {yt_video_link} "
            "Use a plain text question as input to the tool and return an answer.",
        ),
    )
    tools = [assess_question_tool, generate_answer_tool]

    system_prompt = f""" You are a friendly and helpful reviewer whose goal is to review answers to the questions you generate \
        to help a student evaluate their understanding of the topic.
        Plan each step ahead of time before moving on.
        Perform the following actions: 
            1 - Introduce yourself to the students.
            2 - Ask a question from the assess_question tool ONLY.\
            3 - Wait for a response.
            4 - i) First generate your own response by \
                calling the generate_answer_tool with the \
                question from step 2 \
                ii) Then compare your response with the student's response. \
                and figure out the missing components(if any) in the student's answer \
                Generate feedback from these missing components in the student's answer for the student.
                Your feedback should not be more than 4 lines long. 
                    
            5 - Continue the actions from step 2 until the student types "Exit".
        """
    openAIAgentObject = openAIAgent()
    openAIAgentObject.openAI_Agent = OpenAIAgent.from_tools(tools, llm=llm, system_prompt= system_prompt, verbose=True)
    return openAIAgentObject

@app.get("/chat")
def agent_chat(openAIAgent: openAIAgent, query: str) -> str:
    return str(openAIAgent.openAI_Agent.chat(query))