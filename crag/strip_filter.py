from langchain_openai import ChatOpenAI
from prompts import STRIP_FILTER_BOT_SYSTEM_PROMPT
from pydantic import BaseModel
from uuid import uuid4 as getId
import os
from configs import IS_SIMULATION

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("openai_key_loaded_not_set.")

class StripFilterationDetail(BaseModel):
    id:str
    keep:bool

class FilterResponse(BaseModel):
    filters: list[StripFilterationDetail]

stripping_bot = ChatOpenAI(
    model="gpt-5-nano",
    api_key=OPENAI_API_KEY
)

struct_stripping_bot = stripping_bot.with_structured_output(FilterResponse, strict=True)
    

def filter_strips(strips:list[str], query: str)->list[str]:
    if IS_SIMULATION:
        return strips
    
    strips_dict = {str(getId()):s for s in strips}
    
    res:FilterResponse = struct_stripping_bot.invoke([
    (
        "system",
        STRIP_FILTER_BOT_SYSTEM_PROMPT,
    ),
    ("human", f"""given query: {query}
given texts: {"\n".join([f"\nstrip id:{_id}\nstrip text:{_text}" for _id,_text in strips_dict.items()])}
"""),
    ])
    return [ strips_dict[_s.id] for _s in res.filters if _s.keep]