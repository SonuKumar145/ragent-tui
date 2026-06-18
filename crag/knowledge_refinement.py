import re
from langchain_core.documents import Document
from .document_evaluator import score_document, Evaluation
from configs import DOCUMENTATION_EVALUATION_THRESHOLD
from .strip_filter import filter_strips

def convert_to_strips(text:str):
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if len(s.strip())>20]

def filter_docs(scores: list[Evaluation], documents:dict[str,Document], threshold=0.3)->list[Document]:
    return [documents[str(doc_score.id)] for doc_score in scores if documents[str(doc_score.id)] and doc_score.score >=threshold]


def refine_knowledge(query:str, documents:list[Document])->str:
    print("query: ", query)
    refined_knowledge = ""
    
    doc_dict = { doc.id:doc for doc in documents}
    
    scored_documents= score_document(documents, query)
    filtered_documents = filter_docs(scored_documents, doc_dict, threshold=DOCUMENTATION_EVALUATION_THRESHOLD)
    
    for doc in filtered_documents:
        strips = convert_to_strips(doc.page_content)
        filtered_strips = filter_strips(strips, query)
        refined_knowledge = f"{refined_knowledge}\n{"\n".join(filtered_strips)}"
    
    print("refinied knowledge: ", refined_knowledge)
    return refined_knowledge
        


    