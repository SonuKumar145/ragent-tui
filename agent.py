import os
from dotenv import load_dotenv
from langchain_core.documents import Document
from uuid import uuid4
from prompts import SYSTEM_PROMPT

# import chromadb
# from chromadb.utils import embedding_functions

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from deepagents import create_deep_agent

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set.")

DOCUMENTATION_EVALUATION_THRESHOLD=0.3

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma(
    collection_name="hr_faqs",
    embedding_function=embeddings,
    persist_directory="./langchain_chroma/chroma_db"
)

if len(vectorstore.get()["ids"]) == 0:
    documents = list()

    for i, faq in enumerate(FAQ_DOCUMENTS):
        documents.append(Document(
            page_content=f"Q: {faq['question']}\nA: {faq['answer']}"
        ))
    
    vectorstore.add_documents(documents=documents)
    print(f"Ingested {len(FAQ_DOCUMENTS)} FAQ documents.")

@tool
def query_knowledge_base(query: str) -> str:
    """
    Search the company HR/IT knowledge base for documents related to a query.
    Returns the top relevant FAQ text.
    """
    docs = vectorstore.similarity_search(query, k=3)
    if not docs:
        return "No relevant documents found."
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


agent = create_deep_agent(
    model=ChatOpenAI(model="gpt-5-nano", temperature=0.2),
    tools=[query_knowledge_base],
    system_prompt=SYSTEM_PROMPT,
)

print("HR Chatbot with DeepAgents (CRAG logic) ready. Type 'exit' to quit.\n")
messages = []

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ("exit", "quit"):
        break
    if not user_input:
        continue

    messages.append(HumanMessage(content=user_input))

    # Run the agent – it will call tools autonomously and follow the CRAG steps.
    result = agent.invoke({"messages": messages})

    # The agent returns a list of messages; the last AI message is the reply.
    final_answer = result["messages"][-1].content
    print(f"Bot: {final_answer}\n")

    # Keep the full conversation history for the next turn
    messages = result["messages"]