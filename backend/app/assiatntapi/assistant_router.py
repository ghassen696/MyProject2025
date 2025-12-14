from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from new_rag_pipline.retreiver import retrieve_and_answer,retrieve_and_answer_stream
from typing import List, Dict,Optional
import json
router = APIRouter()

class QueryRequest(BaseModel):
    query: str

class Source(BaseModel):
    id: int
    title: str
    product: str
    version: str
    filepath: str
    doc_path: str

class QueryResponse(BaseModel):
    answer: str
    sources: Optional[List[Source]] = None

@router.post("/ask", response_model=QueryResponse)
def ask(request: QueryRequest):
    try:
        result = retrieve_and_answer(request.query)
        return QueryResponse(**result)

    except Exception as e:
        return QueryResponse(
            answer=f"Error retrieving answer: {str(e)}",
            sources=[]
        )

@router.post("/ask/stream")
async def ask_stream(request: QueryRequest):
    """Stream the response token by token"""
    
    async def event_generator():
        try:
            async for event in retrieve_and_answer_stream(request.query):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"  
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )