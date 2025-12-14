from fastapi import APIRouter, Query
from elasticsearch import Elasticsearch
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import pytz

class RawActivityEvent(BaseModel):
    timestamp: int
    event: str
    employee_id: str
    session_id: Optional[str]
    window: Optional[str]
    application: Optional[str]
    control: Optional[str]
    text: Optional[str]
    shortcut_name: Optional[str]
    reason: Optional[str]
    duration_minutes: Optional[float]
    
router = APIRouter()
es = Elasticsearch("http://193.95.30.190:9200")

def get_tunis_today_range():
    """Return start and end of today in Tunis timezone as epoch milliseconds"""
    tz = pytz.timezone("Africa/Tunis")
    now = datetime.now(tz)
    start = tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
    end = tz.localize(datetime(now.year, now.month, now.day, 23, 59, 59, 999000))
        
    print(f"Tunis Today Start: {start} → {start}")
    print(f"Tunis Today End:   {end} → {end}")
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


@router.get("/")
def get_raw_activity(
    employee_id: Optional[str] = None,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    fetch_all: bool = Query(False, description="Fetch all logs ignoring pagination")
):
    """
    Fetch employee raw activity events.
    
    - Standard pagination with page/page_size
    - Use fetch_all=true to get ALL logs (ignores page/page_size)
    - Defaults to today's events in Tunis timezone if start_ts/end_ts not provided
    """
    must = []

    if employee_id:
        must.append({"term": {"employee_id.keyword": employee_id}})

    if start_ts is None and end_ts is None:
        start_ts, end_ts = get_tunis_today_range()
    elif start_ts is None:
        start_ts, _ = get_tunis_today_range()
    elif end_ts is None:
        _, end_ts = get_tunis_today_range()

    must.append({"range": {"timestamp": {"gte": start_ts, "lte": end_ts}}})
    query = {"bool": {"must": must}}

    # If fetch_all=true, use scroll API to get ALL documents
    if fetch_all:
        all_events = []
        
        # Initial search with scroll
        res = es.search(
            index="employee_activity",
            body={
                "query": query,
                "sort": [{"timestamp": {"order": "asc"}}]
            },
            scroll='2m', 
            size=1000,    
        )
        
        scroll_id = res['_scroll_id']
        total = res["hits"]["total"]["value"]
        
        # Get first batch
        all_events.extend([hit["_source"] for hit in res["hits"]["hits"]])
        
        # Continue scrolling until no more results
        while len(res['hits']['hits']) > 0:
            res = es.scroll(scroll_id=scroll_id, scroll='2m')
            all_events.extend([hit["_source"] for hit in res["hits"]["hits"]])
        
        # Clean up scroll context
        es.clear_scroll(scroll_id=scroll_id)
        
        return {
            "total": total,
            "page": 1,
            "page_size": len(all_events),
            "events": all_events,
            "fetched_all": True
        }
    
    # Standard pagination
    from_ = (page - 1) * page_size

    res = es.search(
        index="employee_activity",
        body={
            "query": query,
            "sort": [{"timestamp": {"order": "asc"}}]
        },
        from_=from_,
        size=page_size,
    )

    total = res["hits"]["total"]["value"]
    events = [hit["_source"] for hit in res["hits"]["hits"]]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "events": events,
        "fetched_all": False
    }