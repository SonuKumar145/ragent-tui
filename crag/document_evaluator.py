from langchain_openai import ChatOpenAI
from prompts import DOCUMENT_EVALUATOR_SYSTEM_PROMPT
from pydantic import BaseModel
from langchain_core.documents import Document

class Evaluation(BaseModel):
    id:str
    score:int

class EvaluationResponse(BaseModel):
    scores: list[Evaluation]

document_evaluator = ChatOpenAI(
    model="gpt-5-nano",

)

struct_document_evaluator = document_evaluator.with_structured_output(EvaluationResponse, strict=True)

def score_document(documents:list[Document], query: str):
    res = struct_document_evaluator.invoke([
    (
        "system",
        DOCUMENT_EVALUATOR_SYSTEM_PROMPT,
    ),
    ("human", f"""given query: {query}
given texts: {"\n".join([f"\ndocument id:{d.id}\ndocument page_content:{d.page_content}" for d in documents])}
"""),
    ])
    return res