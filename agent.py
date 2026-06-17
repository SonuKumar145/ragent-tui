import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv, set_key
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

try:
    from utils.message import print_error_string_message, print_warning_string_message, print_ok_string_message, print_inprocess_string_message, print_done_string_message
    from configs import FILE_PATH,COLLECTION_NAME,PERSIST_DIRECTORY_PATH,OPENAI_EMBEDDING_MODEL, IS_SIMULATION, ENV_PATH
        
    env_file_path = Path(ENV_PATH)
        
    if env_file_path.is_file():
        print_ok_string_message("env_file", ".env file found")
    else:
        print_warning_string_message("env_file", ".env file not found")
        env_file_path.touch()
        print_done_string_message("env_file", "empty .env file created")

    load_dotenv(dotenv_path=ENV_PATH)

    print_inprocess_string_message("openai_key", "loading openai key")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        while True:
            user_input = sys.stdin.readline()
            if not user_input or user_input.lower().strip() in ("exit", "quit"):
                break
            success, key, value = set_key(ENV_PATH, "OPENAI_API_KEY", user_input)
            
    print_ok_string_message("openai_key", "openai key loaded")

    from utils.prompts import SYSTEM_PROMPT
    from crag.knowledge_refinement import refine_knowledge
    # import chromadb
    # from chromadb.utils import embedding_functions
    from document_handler.document_loader import load_document
    from chroma.store import add_document_to_vector_db
    from utils.simulation import get_simulated_response


    print_inprocess_string_message("embedding_model","creating embedding model instance" )

    embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)
    print_done_string_message("embedding_model","embedding model instance created")

    print_inprocess_string_message("vector_store","creating vector store instance")
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIRECTORY_PATH
    )

    print_done_string_message("vector_store", "vectorstore instance created")

    if len(vectorstore.get()["ids"]) == 0:
        
        print_warning_string_message("documents","no document found in store")
        file_path = Path(FILE_PATH)
        
        if file_path.is_file():
            
            print_inprocess_string_message("documents", "loadingdocuments in store")
            loaded_documents = load_document(FILE_PATH)
            add_document_to_vector_db(loaded_documents, vectorstore)
            
            print_done_string_message("documents", "documents loaded in store")
        else:
            
            print_error_string_message("documents", "no such file found", FILE_PATH=FILE_PATH)
            raise Exception(f"no such file found {FILE_PATH}")
    else:
        
        print_ok_string_message("documents", "documents found in store")

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

    print_ok_string_message("agent_ready","Agent is ready!")

    messages = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]
    current_message_id = None

    while True:
        user_input = sys.stdin.readline()
        user_input = json.loads(user_input.strip())
        if not user_input.get('message', None) or not user_input.get('message_id', None) or user_input.get('message').lower().strip() in ("exit", "quit"):
            break
        
        if IS_SIMULATION:
            print_ok_string_message("response_stream", "response stream started")
            
            query_result= query_knowledge_base.invoke({"query": user_input.get('message', '')})
            
            for chunk in get_simulated_response(query_result):
                print_ok_string_message("stream_chunk", message=chunk, end="\n", message_id = user_input['message_id'])
            
        else:
            messages.append(HumanMessage(content=user_input.get('message', '')))

            for chunk in llm_with_tools.stream(messages):
                print(chunk.content, end="", flush=True)
                
except Exception as e:
    print_error_string_message("disaster", str(e))