from fastapi import APIRouter, Query
from ..config import ELASTICSEARCH_URL
from pydantic import BaseModel
from typing import List, Optional
from elasticsearch import AsyncElasticsearch
from datetime import datetime

es = AsyncElasticsearch(ELASTICSEARCH_URL)

class EmployeeClassification(BaseModel):
    employee_id: str
    chunk_id: str
    start_time: datetime  # <- use datetime
    end_time: datetime
    window: str
    dominant_event: str
    summary_text: str
    event_count: int
    quality_score: float
    category: str
    confidence: float
    rationale: str

router = APIRouter()

@router.get("/classification", response_model=List[EmployeeClassification])
async def get_classifications(
    employee_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=1000),
    order: str = Query("asc")  # "asc" or "desc"
):
    # Build the query
    query = {"match_all": {}}
    if employee_id and date:
        query = {"bool": {"must": [
            {"match": {"employee_id": employee_id}},
            {"wildcard": {"chunk_id": f"*{date}*"}}
        ]}}
    elif employee_id:
        query = {"match": {"employee_id": employee_id}}
    elif date:
        query = {"wildcard": {"chunk_id": f"*{date}*"}}

    # Elasticsearch search with pagination and sorting
    result = await es.search(
        index="employee_classifications",
        body={
            "query": query,
            "sort": [{"start_time": {"order": order}}]  # <-- order by start_time
        },
        from_=(page-1)*per_page,
        size=per_page
    )

    hits = result.get("hits", {}).get("hits", [])
    return [hit["_source"] for hit in hits]
