from langchain_ollama import ChatOllama
from utils.prompts import DOCUMENT_EVALUATOR_SYSTEM_PROMPT
from pydantic import BaseModel, Field, field_validator
from configs import IS_SIMULATION
from langchain_core.documents import Document
from uuid import UUID
# import os

# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# if not OPENAI_API_KEY:
#     raise ValueError("openai_key_loaded_not_set.")

class Evaluation(BaseModel):
    id:str = Field(
        ..., 
        description="The unique session ID. This MUST be a valid 36-character UUID string (e.g., '123e4567-e89b-12d3-a456-426614174000')."
    )
    score:int
    
    @field_validator('id')
    def check_uuid_format(cls, value: str) -> str:
        try:
            parsed_uuid = UUID(value)
            return str(parsed_uuid)
        except ValueError:
            raise ValueError("The provided ID is not a valid UUID string.")


class EvaluationResponse(BaseModel):
    scores: list[Evaluation]


document_evaluator = ChatOllama(
                model="qwen3.5:4b",
                temperature=0.3,
                num_ctx=16384
            )

struct_document_evaluator = document_evaluator.with_structured_output(EvaluationResponse, strict=True)

def score_document(documents:list[Document], query: str):
    print("going to score these docs: ", [str(doc.id) for doc in documents])
    if IS_SIMULATION:
        return [ Evaluation(id=d.id, score=8) for d in documents]

    res:EvaluationResponse = struct_document_evaluator.invoke([
    (
        "system",
        DOCUMENT_EVALUATOR_SYSTEM_PROMPT,
    ),
    ("human", f"""given query: {query}
given texts: {"\n".join([f"\n{d.id}\ndocument page_content:{d.page_content}" for d in documents])}
"""),
    ], config={"metadata": {"source": "document_evaluator"}, "callbacks":[]})
    print("documents scored!!", ([s.model_dump_json() for s in res.scores]))
    return res.scores