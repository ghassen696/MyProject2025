from fastapi import APIRouter
from pydantic import BaseModel
from rag_pipeline.retreiver import retrieve_and_answer

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str

@router.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    user_query = request.query
    try:
        answer = retrieve_and_answer(user_query)
    except Exception as e:
        answer = f"Error retrieving answer: {str(e)}"
    return QueryResponse(answer=answer)
