from langchain_openai import ChatOpenAI
from utils.prompts import DOCUMENT_EVALUATOR_SYSTEM_PROMPT
from pydantic import BaseModel
from configs import IS_SIMULATION
from langchain_core.documents import Document
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("openai_key_loaded_not_set.")

class Evaluation(BaseModel):
    id:str
    score:int

class EvaluationResponse(BaseModel):
    scores: list[Evaluation]

document_evaluator = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model="gpt-5-nano",
)

struct_document_evaluator = document_evaluator.with_structured_output(EvaluationResponse, strict=True)

def score_document(documents:list[Document], query: str):
    
    if IS_SIMULATION:
        return [ Evaluation(id=d.id, score=8) for d in documents]
    
    res:EvaluationResponse = struct_document_evaluator.invoke([
    (
        "system",
        DOCUMENT_EVALUATOR_SYSTEM_PROMPT,
    ),
    ("human", f"""given query: {query}
given texts: {"\n".join([f"\ndocument id:{d.id}\ndocument page_content:{d.page_content}" for d in documents])}
"""),
    ])
    return res.scores