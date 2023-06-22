import os 
import sys
sys.path.append( os.path.dirname(os.path.dirname(os.path.realpath(__file__))) )
# import utils
import pandas as pd
from Arguments import Arguments

from datastore.factory import get_datastore
from datastore.providers.redis_datastore import RedisDataStore
from models.models import (
    Document,
    DocumentChunk,
    Source,
    DocumentMetadata,
    DocumentChunkMetadata,
    # DocumentMetadataFilter,
    # Query,
    # QueryResult,
    # QueryWithEmbedding,
)
# from models.models import Document, DocumentMetadata, Source
from typing import Dict, List, Optional
import asyncio

arguments = Arguments()
arguments.add(
    '--pickle', type=str, default=None,
    required=True,
    help='pickle file'
)
args = arguments.all()

# datastore = None
# async def test():
#     global datastore
#     datastore = await get_datastore()



# def test(self):
# 	self.client.ping()
# 	print("yo")

# setattr(RedisDataStore, 'test', test)

# db = utils.db_connection()

def get_document_chunks_from_db(pickle_file
    # documents: List[Document], chunk_token_size: Optional[int]
) -> Dict[str, List[DocumentChunk]]:
    """
    Convert a list of documents into a dictionary from document id to list of document chunks.

    Args:
        documents: The list of documents to convert.
        chunk_token_size: The target size of each chunk in tokens, or None to use the default CHUNK_SIZE.

    Returns:
        A dictionary mapping each document id to a list of document chunks, each of which is a DocumentChunk object
        with text, metadata, and embedding attributes.
    """

    # query = "select article_id, chunk, embeddings from poc_gpt_qna_article_embeddings offset %d limit %d" % (offset, limit)
    # rows = utils.read_sql_inmem_uncompressed(query, db)
    documents = pd.read_pickle(pickle_file)
    # documents.columns = ['article_id', 'chunk', 'text', 'content_vector']


    # documents: List[Document] = []
    # article_ids = rows.article_id.unique()
    # for article_id in article_ids:
    #     metadata = DocumentMetadata(
    #         source = Source('file'),
    #         url = "https://medscape.com/viewarticle/%d" % article_id
    #     )
    #     document = Document(metadata=metadata, text="", id=str(article_id))
    #     documents.extend([document])


    # Initialize an empty dictionary of lists of chunks
    chunks: Dict[str, List[DocumentChunk]] = {}

    # # Initialize an empty list of all chunks
    # all_chunks: List[DocumentChunk] = []

    # # Loop over each document and create chunks
    # for doc in documents:
    #     doc_chunks, doc_id = create_document_chunks(doc, chunk_token_size)

    #     # Append the chunks for this document to the list of all chunks
    #     all_chunks.extend(doc_chunks)

    #     # Add the list of chunks for this document to the dictionary with the document id as the key
    #     chunks[doc_id] = doc_chunks

    # # Check if there are no chunks
    # if not all_chunks:
    #     return {}

    article_ids = documents.article_id.unique()
    # article_ids = article_ids[:10]
    for article_id in article_ids:
        doc_id = str(article_id)
        article_chunks = documents[documents['article_id']==article_id]
        doc_chunks: List[DocumentChunk] = []
        metadata = DocumentChunkMetadata(
            document_id = doc_id,
            source = Source('file'),
            url = "https://medscape.com/viewarticle/%s" % doc_id
        )
        temp = []
        for index, row in article_chunks.iterrows():
            temp.append(DocumentChunk(
                id = '%s_%s' % (doc_id, row['chunk']),
                text = "",
                metadata = metadata,
                embedding = list(row['embeddings'])
            ))
        doc_chunks.extend(temp)

        # all_chunks.extend(doc_chunks)
        chunks[doc_id] = doc_chunks

    # # Get all the embeddings for the document chunks in batches, using get_embeddings
    # embeddings: List[List[float]] = []
    # for i in range(0, len(all_chunks), EMBEDDINGS_BATCH_SIZE):
    #     # Get the text of the chunks in the current batch
    #     batch_texts = [
    #         chunk.text for chunk in all_chunks[i : i + EMBEDDINGS_BATCH_SIZE]
    #     ]

    #     # Get the embeddings for the batch texts
    #     batch_embeddings = get_embeddings(batch_texts)

    #     # Append the batch embeddings to the embeddings list
    #     embeddings.extend(batch_embeddings)

    # # Update the document chunk objects with the embeddings
    # for i, chunk in enumerate(all_chunks):
    #     # Assign the embedding from the embeddings list to the chunk object
    #     chunk.embedding = embeddings[i]

    return chunks


chunks = get_document_chunks_from_db(args.pickle)

async def main():
    datastore =await get_datastore()
    await datastore._upsert(chunks)

asyncio.run(main())

# asyncio.run(datastore.test())
