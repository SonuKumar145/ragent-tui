import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from uuid import uuid4
from prompts import SYSTEM_PROMPT
from crag.knowledge_refinement import refine_knowledge
# import chromadb
# from chromadb.utils import embedding_functions

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from deepagents import create_deep_agent
from configs import FILE_PATH,COLLECTION_NAME,PERSIST_DIRECTORY_PATH,OPENAI_EMBEDDING_MODEL
from document_handler.document_loader import load_document
from chroma.store import add_document_to_vector_db

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set.")

embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)

vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=PERSIST_DIRECTORY_PATH
)

if len(vectorstore.get()["ids"]) == 0:
    loaded_documents = load_document(FILE_PATH)
    add_document_to_vector_db(loaded_documents)

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


agent = create_deep_agent(
    model=ChatOpenAI(model="gpt-5-nano", temperature=0.2),
    tools=[query_knowledge_base],
    system_prompt=SYSTEM_PROMPT,
)

print("Chatbot is ready. Query what you want.\nType 'exit' to quit.\n")
messages = []

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ("exit", "quit"):
        break
    if not user_input:
        continue

    messages.append(HumanMessage(content=user_input))

    result = agent.invoke({"messages": messages})

    final_answer = result["messages"][-1].content
    print(f"Bot: {final_answer}\n")

    messages = result["messages"]