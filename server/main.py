import sys
sys.path.append( "/var/www/html/medscape/medscape-content-feed/linear_model/openai_poc/chatgpt-retrieval-plugin/medscape" )

from custom_config import config, utils
# environment = 'local'
# config['LOG_PRINT'] = 0
# config['LOG_NAME'] = 'chat-retrieval-plugin'

# os.environ["REDIS_PORT"] = "7379"
# os.environ["REDIS_DB"] = 1
# from app import config, log

# logLevel = log._nameToLevel.get(config['LOG_LEVEL'].upper())
# logFormat = '[%(asctime)-15s] ' + environment + '.%(levelname)s: %(message)s'
# if config['LOG_DAILY']:
#     config['LOG_NAME'] += datetime.today().strftime("-%m-%d-%Y")

# log.basicConfig(
#     filename = storage_path('logs/%s.log' % config['LOG_NAME']),
#     level = logLevel,
#     format = logFormat
# )

# from dotenv import load_dotenv
# load_dotenv('/var/www/html/medscape/medscape-content-feed/linear_model/.env')

# logFormat = '[%(asctime)-15s] ' + environment + '.%(levelname)s: %(message)s'
# root = log.getLogger()
# logLevel = log._nameToLevel.get('DEBUG')
# root.setLevel(logLevel)

# handler = log.StreamHandler(sys.stdout)
# handler.setLevel(logLevel)
# handler.setFormatter(log.Formatter(logFormat))
# root.addHandler(handler)


import os
from typing import Optional
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Depends, Body, UploadFile
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

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

from models.models import DocumentMetadata, Source

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
assert BEARER_TOKEN is not None


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
#app.mount("/var/www/html/medscape/medscape-content-feed/linear_model/openai_poc/chatgpt-retrieval-plugin/.well-known", StaticFiles(directory=".well-known"), name="static")
# app.mount("/.well-known", StaticFiles(directory="../.well-known"), name="static")
# app.mount("/.well-known", StaticFiles(directory="../.well-known"), name="static")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)


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


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
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
    uvicorn.run("server.main:app", host="0.0.0.0", port=8002, reload=True)


if __name__ == "__main__":
    start()