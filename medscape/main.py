# This is a version of the main.py file found in ../../../server/main.py for testing the plugin locally.
# Use the command `poetry run dev` to run this.

import os
import sys
sys.path.append( os.path.dirname(os.path.realpath(__file__)) )
from custom_config import utils


from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Body, UploadFile

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file

from starlette.responses import FileResponse

from models.models import DocumentMetadata, Source
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

PORT = 3333

origins = [
    f"http://localhost:{PORT}",
    "https://chat.openai.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.route("/.well-known/ai-plugin.json")
async def get_manifest(request):
    file_path = "./medscape/ai-plugin.json"
    return FileResponse(file_path, media_type="text/json")


@app.route("/.well-known/medscape-logo.webp")
async def get_logo(request):
    file_path = "./medscape/medscape-logo.webp"
    return FileResponse(file_path, media_type="image/x-png")


@app.route("/.well-known/openapi.yaml")
async def get_openapi(request):
    file_path = "./medscape/openapi.yaml"
    return FileResponse(file_path, media_type="text/json")


@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except:
        metadata_obj = DocumentMetadata(source=Source.file)

    document = await get_document_from_file(file, metadata_obj)

    try:
        ids = await datastore.upsert([document])
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")


@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
):
    try:
        ids = await datastore.upsert(request.documents)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        ### custom medscape ###
        # add text chunks
        article_ids = []
        chunks = []
        for query in results:
            for chunk in query.results:
                article_id, chunk = chunk.id.split('_')
                article_ids.append(article_id)
                chunks.append(chunk)

        if len(article_ids):
            db = utils.db_connection()
            query = "select article_id, chunk, text from poc_gpt_qna_article_embeddings where article_id in (%s) and chunk in (%s)" % (
                utils.implode(',', article_ids),
                utils.implode(',', chunks)
            )
            df_chunks = utils.read_sql_inmem_uncompressed(query, db)
            if not df_chunks.empty:
                for query in results:
                    for chunk in query.results:
                        article_id, _chunk = chunk.id.split('_')
                        df_chunk = df_chunks[(df_chunks['article_id']==int(article_id)) & (df_chunks['chunk']==int(_chunk))]
                        if not df_chunk.empty:
                            chunk.text = df_chunk.iloc(0)[0].text

        ### custom medscape ###
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("medscape.main:app", host="0.0.0.0", port=PORT, reload=True)
