import os
import json
from typing import List, Dict, Optional, Tuple
from .faq_documents import FAQ_DOCUMENTS

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set.")

client = OpenAI(api_key=OPENAI_API_KEY)
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)

class HRChatbot:
    def __init__(self, collection_name: str = "hr_faqs", k: int = 3):
        self.k = k
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=openai_ef,
        )
        if self.collection.count() == 0:
            self._ingest_faqs()

        # Conversation memory (list of {"role": ..., "content": ...})
        self.history: List[Dict[str, str]] = []

    def _ingest_faqs(self):
        """Insert sample FAQ documents into ChromaDB."""
        ids = [faq["id"] for faq in FAQ_DOCUMENTS]
        documents = [
            f"Question: {faq['question']}\nAnswer: {faq['answer']}"
            for faq in FAQ_DOCUMENTS
        ]
        metadatas = [
            {"question": faq["question"], "answer": faq["answer"]}
            for faq in FAQ_DOCUMENTS
        ]
        self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
        print(f"Ingested {len(FAQ_DOCUMENTS)} FAQ documents.")

    def retrieve(self, query: str, k: Optional[int] = None) -> List[str]:
        """Retrieve top‑k documents from the vector store."""
        k = k or self.k
        results = self.collection.query(query_texts=[query], n_results=k)
        # results['documents'] is a list of lists
        return results["documents"][0] if results["documents"] else []

    def _evaluate_relevance(self, query: str, docs: List[str]) -> Tuple[str, str]:
        """
        Use an LLM to judge relevance of retrieved documents.
        Returns (decision, explanation) where decision is one of:
            FULLY_SUPPORTED, PARTIALLY_SUPPORTED, NOT_SUPPORTED
        """
        if not docs:
            return "NOT_SUPPORTED", "No documents retrieved."

        # Build the evaluation prompt
        prompt = f"""You are a strict relevance evaluator for an HR/support chatbot.
Given a user query and a set of retrieved company documents, decide whether
the documents fully, partially, or do not support answering the query.

User query: "{query}"

Retrieved documents:
"""
        for i, doc in enumerate(docs, 1):
            prompt += f"{i}. {doc}\n"

        prompt += """
Respond with a JSON object exactly in this format:
{{
  "decision": "FULLY_SUPPORTED" | "PARTIALLY_SUPPORTED" | "NOT_SUPPORTED",
  "explanation": "brief reason for the decision"
}}
Do not include any additional text."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=150,
            )
            raw = response.choices[0].message.content.strip()
            result = json.loads(raw)
            return result["decision"], result["explanation"]
        except Exception as e:
            # Fallback: assume not supported
            return "NOT_SUPPORTED", f"Evaluation failed: {str(e)}"

    def _refine_query(self, query: str) -> str:
        """Generate a refined query to improve retrieval."""
        prompt = f"""The original user query below did not return relevant documents
from our company knowledge base. Rewrite the query to be more specific and
better match our HR/IT FAQ documents. Return only the refined query, no
additional commentary.

Original query: "{query}"
Refined query:"""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=100,
            )
            refined = response.choices[0].message.content.strip()
            return refined
        except Exception:
            # Fallback to original query if refinement fails
            return query

    def _generate_answer(
        self, query: str, docs: List[str], conversation_history: List[Dict[str, str]]
    ) -> str:
        """Generate a final answer using the provided documents and chat history."""
        if not docs:
            return (
                "I’m sorry, I couldn’t find any relevant information. "
                "Could you rephrase your question or provide more details?"
            )

        system_message = """You are a helpful HR and IT support assistant for this company.
Answer the user's question using ONLY the information in the provided company documents.
If the documents do not contain enough information, say so clearly and ask for clarification.
Never make up information. Keep your answers concise and professional.

Provided company documents:
"""
        for i, doc in enumerate(docs, 1):
            system_message += f"\n[Doc {i}]: {doc}"

        messages = [{"role": "system", "content": system_message}]
        # Add relevant conversation history (last few turns)
        messages.extend(conversation_history[-6:])  # keep context manageable

        # Ensure the last message is the current user query if not already there
        if messages[-1]["role"] != "user" or messages[-1]["content"] != query:
            messages.append({"role": "user", "content": query})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.2,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def chat(self, user_input: str) -> str:
        """
        Process one user message using the CRAG pipeline and return the bot's reply.
        Maintains conversation history.
        """
        # 1. Add user message to history
        self.history.append({"role": "user", "content": user_input})

        # 2. Initial retrieval
        initial_docs = self.retrieve(user_input)

        # 3. Evaluate relevance
        decision, explanation = self._evaluate_relevance(user_input, initial_docs)

        final_docs = initial_docs
        if decision == "NOT_SUPPORTED":
            # 4. Corrective retrieval: refine query and try again
            refined_query = self._refine_query(user_input)
            # Optional: log the refinement for transparency
            print(f"[System] Refined query: {refined_query}")
            corrective_docs = self.retrieve(refined_query)
            final_docs = corrective_docs

            # Evaluate again; if still not supported, we'll produce a fallback
            decision2, _ = self._evaluate_relevance(refined_query, corrective_docs)
            if decision2 == "NOT_SUPPORTED":
                fallback_msg = (
                    "I wasn’t able to find relevant information for your question. "
                    "Could you provide more details or rephrase it?"
                )
                self.history.append({"role": "assistant", "content": fallback_msg})
                return fallback_msg

        # 5. Generate answer from the final document set
        answer = self._generate_answer(user_input, final_docs, self.history)
        self.history.append({"role": "assistant", "content": answer})
        return answer


# ─── Main loop ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Initializing HR Support Chatbot (CRAG) ...")
    bot = HRChatbot()
    print("Chatbot ready. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() in ("exit", "quit"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        response = bot.chat(user_input)
        print(f"Bot: {response}\n")