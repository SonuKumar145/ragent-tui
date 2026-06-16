import os
import json
from dotenv import load_dotenv

load_dotenv()

print(json.dumps({
    'message':"loading_openai_key"
}), flush=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("openai_key_loaded_not_set.")

print(json.dumps({
    'message':"openai_key_loaded"
}),flush=True)

from prompts import SYSTEM_PROMPT
from crag.knowledge_refinement import refine_knowledge
from pathlib import Path
import sys
# import chromadb
# from chromadb.utils import embedding_functions

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from configs import FILE_PATH,COLLECTION_NAME,PERSIST_DIRECTORY_PATH,OPENAI_EMBEDDING_MODEL, IS_SIMULATION
from document_handler.document_loader import load_document
from chroma.store import add_document_to_vector_db
from simulation import sim_message


print(json.dumps({
    'message':"creating_embedding_model_instance"
}),flush=True)
embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)
print(json.dumps({
    'message':"embedding_model_instance_created"
}),flush=True)

print(json.dumps({
    'message':"creating_vector_store_instance"
}),flush=True)
vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=PERSIST_DIRECTORY_PATH
)
print(json.dumps({
    'message':"vectorstore_instance_created"
}),flush=True)

if len(vectorstore.get()["ids"]) == 0:
    print(json.dumps({
        'message':"no_document_found_in_store"
    }),flush=True)
    file_path = Path(FILE_PATH)
    
    if file_path.is_file():
        loaded_documents = load_document(FILE_PATH)
        add_document_to_vector_db(loaded_documents, vectorstore)
        print(json.dumps({
            'message':"documents_loaded_in_store"
        }),flush=True)
    else:
        raise Exception(json.dumps({
            'FILE_PATH': FILE_PATH,
            'error': f"no_such_file_found"
        }))

@tool
def query_knowledge_base(query: str) -> str:
    """
    Search the company HR/IT knowledge base for documents related to a query.
    Returns the top relevant content.
    """
    docs = vectorstore.similarity_search(query, k=3)
    if not docs:
        return "No relevant documents found."
    return refine_knowledge(query, docs)

llm = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-5-nano", 
    temperature=0.2
    )

llm_with_tools = llm.bind_tools([query_knowledge_base])

print(json.dumps({
    'message':"agent_ready"
}),flush=True)

messages = [
    SystemMessage(content=SYSTEM_PROMPT)
]

while True:
    user_input = sys.stdin.readline()
    
    if not user_input or user_input.lower() in ("exit", "quit"):
        break
    
    if IS_SIMULATION:
        print(json.dumps({"message": "response_stream_start"}), flush=True)
        
        query_result= query_knowledge_base.invoke({"query": user_input})
        
        for chunk in sim_message(query_result):
            payload = {"message": "stream_chunk", "content": chunk}
            print(json.dumps(payload), flush=True)
        
    else:
    
        messages.append(HumanMessage(content=user_input))

        for chunk in llm_with_tools.stream("Explain quantum computing in one paragraph"):
            print(chunk.content, end="", flush=True)

        # final_answer = result["messages"][-1].content

        # messages = result["messages"]