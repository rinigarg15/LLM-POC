# import json
# import os
# from llama_hub.web.beautiful_soup_web.base import BeautifulSoupWebReader
# from llama_hub.youtube_transcript.base import YoutubeTranscriptReader
# from llama_index import ServiceContext, StorageContext, SummaryIndex, load_index_from_storage, set_global_service_context
# from llama_index.schema import Node, NodeWithScore
# from llama_index.storage.docstore import SimpleDocumentStore
# import openai
# from llama_index.llms import OpenAI
# from assess_questions import get_assess_questions_per_node
# from flash_cards import get_flash_cards_per_node
# from generic_helper import Topics
# from llama_index.response_synthesizers import ResponseMode, get_response_synthesizer
# from persistence import from_persist_path, persist, from_persist_path_line
# from llama_index.chat_engine.context import ContextChatEngine

# DEFAULT_TOPICS_STORE = "./topics_data/"
# RAG_STORE = "RAG/"
# DETAILED_SUMMARY_STORE = "detailed_summary"
# FLASH_CARDS_STORE = "flash_cards"
# QA_KEY_STORE = "QA_Key"
# KEY_IDEA_STORE = "key_idea"
# SUMMARY_STORE = "summary"

# url1 = 'https://research.ibm.com/blog/retrieval-augmented-generation-RAG'
# url2 = 'https://www.datastax.com/guides/what-is-retrieval-augmented-generation?filter=%7B%7D'
# url3 = 'https://colabdoge.medium.com/what-is-rag-retrieval-augmented-generation-b0afc5dd5e79'
# url4 = 'https://prateekjoshi.substack.com/p/what-is-retrieval-augmented-generation'
# url5 = 'https://www.techtarget.com/searchenterpriseai/definition/retrieval-augmented-generation'
# yt_video_link = 'https://www.youtube.com/watch?v=uCTBNMEPNtQ'
# nodes = []
# index = None

# def create_RAG_topic():
#     initialize_RAG_index()
#     store_summary()
#     store_flash_cards()
#     store_QAKey()

# def initialize_RAG_index():
#     global index
#     global nodes
#     openai.api_key = os.getenv("OPENAI_API_KEY")

#     llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
#     service_context = ServiceContext.from_defaults(llm=llm)
#     set_global_service_context(service_context=service_context)
#     index_name = "index_" + Topics.RAG.value
#     index_location = "./topic_indexes/"+index_name

#     if os.path.exists(index_location):
#         index = load_index_from_storage(
#             StorageContext.from_defaults(persist_dir=index_location), service_context=service_context
#         )
#         nodes = index.docstore.docs.values()
#     else:
#         loader = BeautifulSoupWebReader()
#         documents = loader.load_data(urls=[url1, url2, url3, url4, url5])

#         loader = YoutubeTranscriptReader()
#         transcript_document = loader.load_data(ytlinks=[yt_video_link])
#         transcript_document[-1].extra_info = {"URL": yt_video_link}
#         documents.extend(transcript_document)

#         nodes = []
#         for doc  in documents:
#             node = Node(text = doc.get_content())
#             nodes.append(node)
#         docstore = SimpleDocumentStore()
#         docstore.add_documents(nodes)

#         storage_context = StorageContext.from_defaults(docstore=docstore)
#         index = SummaryIndex(nodes, service_context=service_context, storage_context=storage_context)
#         index.storage_context.persist(persist_dir=index_location)

# def store_summary():
#     response_synthesizer = get_response_synthesizer(
#         response_mode='tree_summarize')

#     query_text = f"""
#         You are an upbeat and friendly tutor with an encouraging tone.\
#         Your goal is to generate a detailed summary of the context information above.
#         Do not miss any key points in your summary and don't be repetitve.
#     """

#     nodes_with_score = [NodeWithScore(node= node, score = 1.0) for node in nodes]

#     response = response_synthesizer.synthesize(
#         query_text,
#         nodes=nodes_with_score
#     )
#     persist(DEFAULT_TOPICS_STORE + RAG_STORE + DETAILED_SUMMARY_STORE, response.response)

# def store_flash_cards():
#     num_flash_cards = 20
#     node_text = from_persist_path_line(DEFAULT_TOPICS_STORE + RAG_STORE + DETAILED_SUMMARY_STORE)
#     response = get_flash_cards_per_node(node_text, num_flash_cards)
#     flash_cards = []
#     for chunk in response:
#         flash_card = json.loads(chunk)
#         flash_cards.append(flash_card)
#     persist(DEFAULT_TOPICS_STORE + RAG_STORE + FLASH_CARDS_STORE, flash_cards)

# def store_QAKey():
#     node_text = from_persist_path_line(DEFAULT_TOPICS_STORE + RAG_STORE + DETAILED_SUMMARY_STORE)
#     response = get_assess_questions_per_node(node_text)
#     QAs = []
#     for chunk in response:
#         QA = json.loads(chunk)
#         QAs.append(QA)
#     persist(DEFAULT_TOPICS_STORE + RAG_STORE + QA_KEY_STORE, QAs)

# def store_key_idea(word_limit: int):
#     response_synthesizer = get_response_synthesizer(
#         response_mode='tree_summarize')

#     query_text = f"""
#         You are an upbeat and friendly tutor with an encouraging tone.\
#         Generate one Key Idea of the context information provided.
#         Use no more than {word_limit} words for your Key Idea.
#         Highlight the important concepts in bold.
#     """

#     nodes_with_score = [NodeWithScore(node= node, score = 1.0) for node in nodes]

#     response = response_synthesizer.synthesize(
#         query_text,
#         nodes=nodes_with_score
#     )
#     persist(DEFAULT_TOPICS_STORE + RAG_STORE + KEY_IDEA_STORE,response.response)

# def store_key_idea_summary(word_limit: int):
#     response_synthesizer = get_response_synthesizer(
#         response_mode='tree_summarize')

#     query_text = f"""
#         You are an upbeat and friendly tutor with an encouraging tone.\
#         Provide Key Insights from the context information ONLY.
#         For each key insight, provide relevant summary in the form of bullet points.
#         Use no more than {word_limit} words in your summary.
#         Highlight the important words in your summary in bold.
#     """

#     nodes_with_score = [NodeWithScore(node= node, score = 1.0) for node in nodes]

#     response = response_synthesizer.synthesize(
#         query_text,
#         nodes=nodes_with_score
#     )
#     persist(DEFAULT_TOPICS_STORE + RAG_STORE + SUMMARY_STORE, response.response)

# def get_stored_flash_cards_generator():
#     file_name = DEFAULT_TOPICS_STORE + RAG_STORE + FLASH_CARDS_STORE
#     flash_cards = from_persist_path(file_name)
#     for row in flash_cards:
#         json_data = json.dumps({"front": row["front"], "back": row["back"]})
#         yield json_data + "\n"

# def get_stored_QAKey_generator():
#     file_name = DEFAULT_TOPICS_STORE + RAG_STORE + QA_KEY_STORE
#     QA_key = from_persist_path(file_name)
#     for row in QA_key:
#         json_data = json.dumps({"question": row["question"], "answer": row["answer"]})
#         yield json_data + "\n"

# def get_stored_QAKey():
#     file_name = DEFAULT_TOPICS_STORE + RAG_STORE + QA_KEY_STORE
#     return from_persist_path(file_name)

# def get_stored_key_idea_generator():
#     file_name = DEFAULT_TOPICS_STORE + RAG_STORE + KEY_IDEA_STORE
#     for row in open(file_name, "r"):
#         yield row

# def get_stored_summary_generator():
#     file_name = DEFAULT_TOPICS_STORE + RAG_STORE + SUMMARY_STORE
#     for row in open(file_name, "r"):
#         yield row

# def create_chat_engine_topic():
#     retriever = index.as_retriever()

#     response_synthesizer = get_response_synthesizer(response_mode=ResponseMode.COMPACT, use_async = True, streaming = True)

#     system_prompt = f""" You are a friendly and helpful mentor whose task is to \ 
#         use ONLY the context information and no other sources to answer the question being asked.\
#         If you don't find an answer within the context, SAY 'Sorry, I could not find the answer within the context.' \ 
#         and DO NOT provide a generic response."""
    
#     chat_engine = ContextChatEngine.from_defaults(system_prompt = system_prompt, retriever = retriever, response_synthesizer = response_synthesizer)
#     return chat_engine