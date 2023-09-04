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


def initialize_index(yt_video_link: str):
    openai.api_key = os.getenv("OPENAI_API_KEY")

    llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
    service_context = ServiceContext.from_defaults(llm=llm)
    set_global_service_context(service_context=service_context)

    index_name = "index_" + yt_video_link.split("?v=")[-1]
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
    return index
