from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from elasticsearch import Elasticsearch
import pytz

router = APIRouter()
es = Elasticsearch("http://localhost:9200")  # adjust if needed
INDEX_NAME = "employee_requests"
if not es.indices.exists(index=INDEX_NAME):
    es.indices.create(
        index=INDEX_NAME,
        body={
            "mappings": {
                "properties": {
                    "employee_id": {"type": "keyword"},
                    "request_type": {"type": "keyword"},
                    "idle_id": {"type": "keyword"},
                    "requested_pause_type": {"type": "keyword"},
                    "effective_duration_sec": {"type": "float"},
                    "start_ts": {"type": "date"},
                    "end_ts": {"type": "date"},
                    "reason": {"type": "text"},
                    "status": {"type": "keyword"},
                    "requested_at": {"type": "date"}
                }
            }
        }
    )
# Pause types and maximum durations (seconds)
PAUSE_TYPES = {
    "lunch": 60 * 60,
    "bathroom": 15 * 60,
    "phone_call": 10 * 60,
    "meeting": 2 * 60 * 60,
    "personal_break": 15 * 60
}

# ------------------- Pydantic Models ------------------- #
class IdleCorrectionRequest(BaseModel):
    employee_id: str
    idle_id: str
    requested_pause_type: str
    reason: str

class DayExclusionRequest(BaseModel):
    employee_id: str
    date: Optional[str] = None  # YYYY-MM-DD, defaults to today
    reason: str

# ------------------- Helper Functions ------------------- #
def get_tunis_today_range():
    tz = pytz.timezone("Africa/Tunis")
    now = datetime.now(tz)
    start = tz.localize(datetime(now.year, now.month, now.day, 0, 0, 0))
    end = tz.localize(datetime(now.year, now.month, now.day, 23, 59, 59, 999000))
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

def validate_pause_duration(idle_duration_sec: float, requested_pause_type: str) -> float:
    """Return the effective duration that can be applied to this pause type"""
    max_allowed = PAUSE_TYPES.get(requested_pause_type)
    if max_allowed is None:
        raise HTTPException(status_code=400, detail="Invalid pause type")
    return min(idle_duration_sec, max_allowed)

# ------------------- Routes ------------------- #
@router.post("/idle")
def request_idle_correction(req: IdleCorrectionRequest):
    # Fetch the idle event from ES to validate duration
    res = es.search(
        index="employee_activity",
        query={
            "bool": {
                "must": [
                    {"term": {"employee_id.keyword": req.employee_id}},
                    {"term": {"idle_id.keyword": req.idle_id}}
                ]
            }
        }
    )
    hits = res["hits"]["hits"]
    if not hits:
        raise HTTPException(status_code=404, detail="Idle event not found")
    
    idle_event = hits[0]["_source"]
    effective_duration = validate_pause_duration(
        idle_event.get("idle_duration_sec", 0),
        req.requested_pause_type
    )

    doc = {
        "employee_id": req.employee_id,
        "request_type": "Idle Correction",
        "idle_id": req.idle_id,
        "requested_pause_type": req.requested_pause_type,
        "effective_duration_sec": effective_duration,
        "reason": req.reason,
        "status": "pending",
        "requested_at": int(datetime.utcnow().timestamp() * 1000)
    }
    es.index(index="employee_requests", document=doc)
    return {"message": "Idle correction request submitted", "effective_duration_sec": effective_duration}


@router.post("/day_exclusion")
def request_day_exclusion(req: DayExclusionRequest):
    # Default to today if date not provided
    tz = pytz.timezone("Africa/Tunis")
    if req.date:
        try:
            date_obj = datetime.strptime(req.date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        date_obj = datetime.now(tz)
    
    start = tz.localize(datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0, 0))
    end = tz.localize(datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59, 999000))

    doc = {
        "employee_id": req.employee_id,
        "request_type": "Day Exclusion",
        "start_ts": int(start.timestamp() * 1000),
        "end_ts": int(end.timestamp() * 1000),
        "reason": req.reason,
        "status": "pending",
        "requested_at": int(datetime.utcnow().timestamp() * 1000)
    }
    es.index(index="employee_requests", document=doc)
    return {"message": f"Day exclusion request submitted for {date_obj.date()}"}
@router.get("/employee/{employee_id}")
def get_employee_requests(
    employee_id: str,
    status: Optional[str] = None,
    page: int = 1,          # frontend will send page number
    page_size: int = 20     # frontend will send page size
):
    """
    Fetch requests for a given employee with pagination.
    """
    must = [{"term": {"employee_id": employee_id}}]
    
    if status:
        must.append({"match": {"status": status.lower()}})

    query = {"bool": {"must": must}}
    
    # Calculate from offset
    from_ = (page - 1) * page_size
    
    res = es.search(
        index="employee_requests",
        query=query,
        sort=[{"requested_at": {"order": "desc"}}],
        from_=from_,
        size=page_size
    )
    
    requests = [hit["_source"] for hit in res["hits"]["hits"]]
    total = res["hits"]["total"]["value"]
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "requests": requests
    }
