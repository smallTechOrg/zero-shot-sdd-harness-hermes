from pydantic import BaseModel

class QueryRequest(BaseModel):
    session_id: str | None = None
    question: str
    data_source: str = "cache"
    sources: list[str] | None = None
