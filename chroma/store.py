from langchain_core.documents import Document
from document_handler.chunker import chunk_document
from langchain_chroma import Chroma

def add_document_to_vector_db(documents:list[Document], chroma_store:Chroma):
    for doc in documents:
        chunks = chunk_document(doc.page_content)
        chroma_store.add_texts(chunks)