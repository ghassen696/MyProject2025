from fastapi import APIRouter, HTTPException, Query
from ..config import ELASTICSEARCH_URL
from elasticsearch import AsyncElasticsearch
from pydantic import BaseModel
from typing import Dict, List, Optional

class EmployeeSummary(BaseModel):
    employee_id: str
    date: str
    summary: str
    activities: Dict[str, List[str]]
    insights: List[str]
    generated_at: Optional[str]

es = AsyncElasticsearch(ELASTICSEARCH_URL)
router = APIRouter()

@router.get("/summarie", response_model=List[EmployeeSummary])
async def get_summaries(employee_id: str = Query(None), date: str = Query(None)):
    query = {"match_all": {}}

    if employee_id and date:
        query = {"bool": {"must": [
            {"match": {"employee_id": employee_id}},
            {"match": {"date": date}}
        ]}}
    elif employee_id:
        query = {"match": {"employee_id": employee_id}}
    elif date:
        query = {"match": {"date": date}}

    result = await es.search(index="employee_daily_summaries", body={"query": query})
    hits = result.get("hits", {}).get("hits", [])

    return [hit["_source"] for hit in hits]
