import json
import math
import os
from llama_hub.web.beautiful_soup_web.base import BeautifulSoupWebReader
from llama_hub.youtube_transcript.base import YoutubeTranscriptReader
from llama_index import ServiceContext, StorageContext, SummaryIndex, load_index_from_storage, set_global_service_context
from llama_index.schema import Document, Node
from llama_index.storage.docstore import SimpleDocumentStore
import openai
from llama_index.llms import OpenAI
from assess_questions import get_assess_questions_per_node
from flash_cards import get_flash_cards_per_node
from generic_helper import Topics
from llama_index.retrievers import VectorIndexRetriever
from llama_index.response_synthesizers import get_response_synthesizer
from llama_index.query_engine import RetrieverQueryEngine
from persistence import from_persist_path, persist

url1 = 'https://research.ibm.com/blog/retrieval-augmented-generation-RAG'
url2 = 'https://www.datastax.com/guides/what-is-retrieval-augmented-generation?filter=%7B%7D'
url3 = 'https://colabdoge.medium.com/what-is-rag-retrieval-augmented-generation-b0afc5dd5e79'
url4 = 'https://prateekjoshi.substack.com/p/what-is-retrieval-augmented-generation'
url5 = 'https://www.techtarget.com/searchenterpriseai/definition/retrieval-augmented-generation'
yt_video_link = 'https://www.youtube.com/watch?v=uCTBNMEPNtQ'

def create_RAG_topic():
    initialize_RAG_index()
    store_summary()
    store_flash_cards()
    store_QAKey()

def initialize_RAG_index():
    openai.api_key = os.getenv("OPENAI_API_KEY")

    llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
    service_context = ServiceContext.from_defaults(llm=llm)
    set_global_service_context(service_context=service_context)
    index_name = "index_" + Topics.RAG.value
    index_location = "./topic_indexes/"+index_name

    if os.path.exists(index_location):
        index = load_index_from_storage(
            StorageContext.from_defaults(persist_dir=index_location), service_context=service_context
        )
    else:
        loader = BeautifulSoupWebReader()
        documents = loader.load_data(urls=[url1, url2, url3, url4, url5])

        loader = YoutubeTranscriptReader()
        transcript = loader.load_data(ytlinks=[yt_video_link])
        documents.append(Document(text=transcript, extra_info={"URL": yt_video_link}))

        nodes = []
        for doc  in documents:
            node = Node(text = doc.get_content())
            nodes.append(node)
        docstore = SimpleDocumentStore()
        docstore.add_documents(nodes)

        storage_context = StorageContext.from_defaults(docstore=docstore)
        index = SummaryIndex(nodes, service_context=service_context, storage_context=storage_context)
        index.storage_context.persist(persist_dir=index_location)

    return index

def get_key_ideas_from_transcript(word_limit: int):
    index = initialize_RAG_index()

    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize')

    query_text = f"""
        You are an upbeat and friendly tutor with an encouraging tone.\
        Generate one Key Idea of the context information provided.
        Use no more than {word_limit} words for your Key Idea.
        Highlight the important concepts in bold.
    """

    response = response_synthesizer.synthesize(
        query_text,
        nodes=index.docstore.docs
    )

    persist("./topics/RAG/key_idea", response)

def generate_key_insight_with_summary(transcript: str, word_limit: int):
    llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
    key_idea_word_limit = int(0.2*word_limit)
    elaboration_word_limit = word_limit - key_idea_word_limit
    bullet_points = math.ceil(elaboration_word_limit/15)

    prompt = f"""
        context_information: {transcript}

        You are an upbeat and friendly tutor with an encouraging tone who has been provided the context_information. \n"
        Your goal is to generate a concise Summary in no more than {word_limit} words using ONLY the context information and no other sources.
        Perform the following actions :-
            1) Generate one Key Idea from the context_information ONLY in no more than {key_idea_word_limit} words.\n"
            2) Elaborate your Key Idea in no more than {bullet_points} bullet points . \n
            Your elaboration should not be in more than {elaboration_word_limit} words\n"
            3) Format the key points in **bold** and *italicize* any relevant phrases \n"
        Use the following format for your final output:
            Key Idea: <Key Idea>
            <elaboration>
    """

    response = llm.complete(prompt)
    persist("./topics/RAG/key_insight_with_summary", response)

def store_summary():
    index = initialize_RAG_index()
    response_synthesizer = get_response_synthesizer(
        response_mode='tree_summarize')

    query_text = f"""
        You are an upbeat and friendly tutor with an encouraging tone.\
        Your goal is to generate a detailed summary of the context information above.
        Do not miss any key points in your summary and don't be repetitve.
    """

    response = response_synthesizer.synthesize(
        query_text,
        nodes=index.docstore.docs
    )
    persist("./topics_data/RAG/detailed_summary", response)

def store_flash_cards():
    num_flash_cards = 20
    node_text = from_persist_path("./topics_data/RAG/detailed_summary")
    response = get_flash_cards_per_node(node_text, num_flash_cards)
    for chunk in response:
        flash_card = json.loads(chunk)
        persist("./topics_data/RAG/flash_cards", flash_card)

def store_QAKey():
    node_text = from_persist_path("./topics_data/RAG/detailed_summary")
    response = get_assess_questions_per_node(node_text)
    for chunk in response:
        QA = json.loads(chunk)
        persist("./topics_data/RAG/QA_Key", QA)

def get_flash_cards():
    file_name = "./topics_data/RAG/flash_cards"
    for row in open(file_name, "r"):
        yield row

def get_QAKey():
    file_name = "./topics_data/RAG/QA_Key"
    for row in open(file_name, "r"):
        yield row