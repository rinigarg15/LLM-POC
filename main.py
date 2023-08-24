from fastapi import FastAPI
import os
import openai
from llama_index.llms.openai import OpenAI
from llama_index.llms.base import ChatMessage
from llama_index.retrievers import VectorIndexRetriever
from llama_index.response_synthesizers import get_response_synthesizer
from llama_index.query_engine import RetrieverQueryEngine
from llama_index.node_parser import SimpleNodeParser
from llama_index.chat_engine.context import ContextChatEngine
from pydantic import BaseConfig, BaseModel
from llama_index.text_splitter import TokenTextSplitter
from llama_index.program.openai_program import OpenAIPydanticProgram
from typing import List
from llama_index import (
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
    set_global_service_context,
    load_index_from_storage,
    download_loader,
)

app = FastAPI()
BaseConfig.arbitrary_types_allowed = True


def initialize_index(yt_video_link: str):
    index_name = "index_" + yt_video_link.split("?v=")[-1]
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

        node_parser = SimpleNodeParser(text_splitter=TokenTextSplitter())
        nodes = node_parser.get_nodes_from_documents(documents)

        index = VectorStoreIndex(nodes, service_context=service_context)

        index.storage_context.persist(persist_dir=index_location)
    return index


@app.get("/get_transcript_summary")
def get_transcript_summary(yt_video_link: str) -> str:

    index = initialize_index(yt_video_link)
    retriever = VectorIndexRetriever(
        index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize')

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
    retriever = VectorIndexRetriever(
        index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize')

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
    retriever = VectorIndexRetriever(
        index=index, similarity_top_k=len(index.docstore.docs))
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize')

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


class QAPair(BaseModel):
    """A question-answer pair."""
    question: str
    answer: str


class QAList(BaseModel):
    """A list of QAPairs."""
    questions_answers_list: List[QAPair]


@app.get("/get_assess_questions")
def get_assess_questions(yt_video_link: str) -> List[QAPair]:
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


@app.get("/get_assessment")
def get_assessment(question: str, answer: str, student_answer: str) -> str:
    prompt = f"""
        question: {question}
        correct_answer: {answer}
        students_answer: {student_answer}

        You are a friendly and helpful reviewer who has been the given the correct_answer\
        and a students_answer to a question. Your goal is to review the students_answer to the question \
        by comparing it with the correct_answer and generate appropriate feedback.

        Perform the following actions :-
            1) Check if the students_answer is correct by comparing it with ONLY the correct_answer.\
                You can use ONLY question for context information.

            2) If the students_answer is correct, figure out the [missing components](if any) in the students_answer \
                by comparing it with ONLY the correct_answer. Use ONLY question for context information.

            3) If there are any[missing components], generate feedback for the student from these missing components.

            Use the following format for your final output:

            Correct: <Yes or No or Partially Correct>

            Feedback: <Feedback>

            Correct Answer: <correct_answer>     
    """
    openAI = OpenAI(temperature=0)
    messages = [ChatMessage(content=prompt)]
    response = openAI.chat(messages)
    return response.raw.choices[0].message["content"]
