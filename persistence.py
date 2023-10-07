import json
import os
from typing import Optional
import fsspec
from video_helper import extract_video_id

DEFAULT_NODE_TEXT_LIST_KEY = "node_text_list"

def persist(persist_path, data, fs: Optional[fsspec.AbstractFileSystem] = None ):
    fs = fs or fsspec.filesystem("file")
    dirpath = os.path.dirname(persist_path)
    if not fs.exists(dirpath):
        fs.makedirs(dirpath)

    with fs.open(persist_path, "a") as f:
        f.write(json.dumps(data))

def persist_node_texts(yt_video_link: str, index):
    video_id = extract_video_id(yt_video_link)
    nodes = index.docstore.docs
    node_text_list = list(node.text for node in nodes.values())
    nodes_text_dict = {DEFAULT_NODE_TEXT_LIST_KEY: node_text_list}
    persist(persist_path= "./disk_data/"+video_id, data=nodes_text_dict)

def from_persist_path(yt_video_link: str, fs: Optional[fsspec.AbstractFileSystem] = None):
    video_id = extract_video_id(yt_video_link)
    persist_path= "./disk_data/"+video_id
    
    fs = fs or fsspec.filesystem("file")
    with fs.open(persist_path, "rb") as f:
        data = json.load(f)
    return data