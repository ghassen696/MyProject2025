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
es = Elasticsearch("http://localhost:9200")  # adjust if using config

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
    page: int = 1,         # new
    page_size: int = 100   # new
):
    """
    Fetch employee raw activity events with pagination.
    Defaults to today's events in Tunis timezone if start_ts/end_ts not provided.
    """
    must = []

    if employee_id:
        must.append({"term": {"employee_id.keyword": employee_id}})

    if start_ts is None or end_ts is None:
        start_ts, end_ts = get_tunis_today_range()

    range_query = {}
    if start_ts is not None:
        range_query["gte"] = start_ts
    if end_ts is not None:
        range_query["lte"] = end_ts
    must.append({"range": {"timestamp": range_query}})

    query = {"bool": {"must": must}}

    # calculate offset
    from_ = (page - 1) * page_size

    res = es.search(
        index="employee_activity",
        body={
            "query": query,
            "sort": [{"timestamp": {"order": "asc"}}]
        },
        from_=from_,
        size=page_size
    )

    total = res["hits"]["total"]["value"]
    events = [hit["_source"] for hit in res["hits"]["hits"]]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "events": events
    }
