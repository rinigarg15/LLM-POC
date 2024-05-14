from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from packs.embedded import EmbeddedTablesUnstructuredRetrieverPack
import os


router = APIRouter()
    

@router.get("/response")
def response(query: str):
    embedded_tables_unstructured_pack = EmbeddedTablesUnstructuredRetrieverPack(
        os.getenv("HTML_PATH"),
        nodes_save_path=os.getenv("PKL_PATH")
    )
    response = embedded_tables_unstructured_pack.run(query)
    return response.response