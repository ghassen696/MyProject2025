from fastapi import APIRouter, Depends
from ..config import ELASTICSEARCH_URL, INDEX_KPIBATCH
from .kpibatch_services import transform_es_doc
from .models import ProductivityData
from elasticsearch import AsyncElasticsearch

es = AsyncElasticsearch(ELASTICSEARCH_URL)

router = APIRouter(prefix="/productivity", tags=["Productivity"])

@router.get("/{employee_id}/{date}", response_model=ProductivityData)
async def get_productivity(employee_id: str, date: str):
    doc_id = f"{employee_id}-{date}"
    resp = await es.get(index=INDEX_KPIBATCH, id=doc_id, ignore=[404])

    if not data:
        raise HTTPException(status_code=404, detail="Productivity data not found")
    if not resp.get("found"):
        return {"error": "No data found"}

    return transform_es_doc(resp)

# kpibatch_router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from ..config import ELASTICSEARCH_URL, INDEX_KPIBATCH
from .kpibatch_services import transform_es_doc, aggregate_productivity_docs
from .models import ProductivityData
from elasticsearch import AsyncElasticsearch
from app.auth.dependencies import get_current_user

es = AsyncElasticsearch(ELASTICSEARCH_URL)

router = APIRouter(prefix="/productivity", tags=["Productivity"])

@router.get("/", response_model=ProductivityData)
async def get_productivity_data(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD"),
    employee_id: Optional[str] = Query(None, description="Employee ID (optional for team view)"),
):
    """
    - Regular users: only their own data
    - Admin: can choose one employee, or none (for team-level avg)
    - Supports single-day and range queries
    """


    # Build the Elasticsearch query
    query_filters = [{"range": {"date": {"gte": start_date, "lte": end_date}}}]
    if employee_id:
        query_filters.append({"term": {"employee_id": employee_id}})

    query = {"bool": {"must": query_filters}}

    # Fetch all matching docs
    resp = await es.search(index=INDEX_KPIBATCH, query=query, size=5000)
    hits = resp["hits"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail="No data found for the selected range")

    # Transform ES docs
    docs = [transform_es_doc(hit,start_date, end_date) for hit in hits]

    # Aggregate if multiple docs (team view or multi-day)
    if len(docs) > 1:
        aggregated = aggregate_productivity_docs(docs)
        return aggregated
    else:
        # Single document → return directly
        return docs[0]
"""
from fastapi import APIRouter, Depends
from ..config import ELASTICSEARCH_URL, INDEX_KPIBATCH
from .kpibatch_services import transform_es_doc
from .models import ProductivityData
from elasticsearch import AsyncElasticsearch

es = AsyncElasticsearch(ELASTICSEARCH_URL)

router = APIRouter(prefix="/productivity", tags=["Productivity"])

@router.get("/{employee_id}/{date}", response_model=ProductivityData)
async def get_productivity(employee_id: str, date: str):
    doc_id = f"{employee_id}-{date}"
    resp = await es.get(index=INDEX_KPIBATCH, id=doc_id, ignore=[404])
    if not resp.get("found"):
        return {"error": "No data found"}

    return transform_es_doc(resp)
"""
