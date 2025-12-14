from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from elasticsearch import Elasticsearch
import pytz
from .requests_routes import PAUSE_TYPES
router = APIRouter()
es = Elasticsearch("http://193.95.30.190:9200")  # adjust if needed

# ------------------- Helper Functions ------------------- #
def get_tunis_day_range(date_str: Optional[str] = None):
    tz = pytz.timezone("Africa/Tunis")
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        date_obj = datetime.now(tz)
    
    start = tz.localize(datetime(date_obj.year, date_obj.month, date_obj.day, 0, 0, 0))
    end = tz.localize(datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, 59, 999000))
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)

# ------------------- Admin Routes ------------------- #

@router.get("/logs")
def view_logs(
    employee_id: Optional[str] = None,
    date: Optional[str] = None,
    from_: int = 0,
    size: int = 100
):
    """
    Admin view of all employee logs.
    Filter by employee_id and/or date (YYYY-MM-DD).
    Supports pagination.
    """
    start_ts, end_ts = get_tunis_day_range(date)
    
    must = [{"range": {"timestamp": {"gte": start_ts, "lte": end_ts}}}]
    
    if employee_id:
        must.append({"term": {"employee_id.keyword": employee_id}})
    
    query = {"bool": {"must": must}}
    
    res = es.search(
        index="employee_activity",
        query=query,
        sort=[{"timestamp": {"order": "asc"}}],
        from_=from_,
        size=size
    )
    
    events = [hit["_source"] for hit in res["hits"]["hits"]]
    total = res["hits"]["total"]["value"]
    
    return {"total": total, "events": events}


@router.get("/requests")
def view_requests(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,  # pending, approved, declined
    date: Optional[str] = None,
    from_: int = 0,
    size: int = 100
):
    """
    Admin view of all requests.
    Can filter by employee_id, status, or date.
    """
    must = []
    
    if employee_id:
        must.append({"term": {"employee_id": employee_id}})
    
    if status:
        must.append({"term": {"status": status}})
    
    if date:
        start_ts, end_ts = get_tunis_day_range(date)
        must.append({"range": {"requested_at": {"gte": start_ts, "lte": end_ts}}})
    
    query = {"bool": {"must": must}}
    
    res = es.search(
        index="employee_requests",
        query=query,
        sort=[{"requested_at": {"order": "desc"}}],
        from_=from_,
        size=size
    )
    
    requests = [{"_id": hit["_id"], **hit["_source"]} for hit in res["hits"]["hits"]]
    total = res["hits"]["total"]["value"]
    
    return {"total": total, "requests": requests}


@router.post("/requests/{request_id}/decision")
def decide_request(request_id: str, decision: str = Query(..., regex="^(approved|declined)$")):
    """
    Admin can approve or decline a request.
    Day Exclusion => delete logs in that day.
    Idle Correction => update start/end timestamps and duration.
    """
    # Fetch the request
    res = es.get(index="employee_requests", id=request_id, ignore=[404])
    if not res or "_source" not in res:
        raise HTTPException(status_code=404, detail="Request not found")

    request_doc = res["_source"]

    # Update request status
    es.update(index="employee_requests", id=request_id, doc={"status": decision})

    # Only process approved requests
    if decision != "approved":
        return {"message": f"Request {request_id} {decision}"}

    employee_id = request_doc["employee_id"]

    # ------------------- Day Exclusion ------------------- #
    if request_doc["request_type"] == "Day Exclusion":
        start_ts = request_doc["start_ts"]
        end_ts = request_doc["end_ts"]

        es.delete_by_query(
            index="employee_activity",
            query={
                "bool": {
                    "must": [
                        {"term": {"employee_id.keyword": employee_id}},
                        {"range": {"timestamp": {"gte": start_ts, "lte": end_ts}}}
                    ]
                }
            },
            refresh=True  # ensure changes are immediately visible
        )

    # ------------------- Idle Correction ------------------- #
# ------------------- Idle Correction ------------------- #
    elif request_doc["request_type"] == "Idle Correction":
        idle_id = request_doc["idle_id"]
        requested_pause_type = request_doc["requested_pause_type"]

        # 1️⃣ Fetch idle interval from ES
        res = es.search(
            index="employee_activity",
            query={
                "bool": {
                    "must": [
                        {"term": {"employee_id.keyword": employee_id}},
                        {"term": {"idle_id.keyword": idle_id}}
                    ]
                }
            },
            sort=[{"timestamp": {"order": "asc"}}]
        )
        hits = res["hits"]["hits"]
        if not hits:
            raise HTTPException(status_code=404, detail="Idle event not found")

        idle_start_ts = hits[0]["_source"]["timestamp"]
        idle_end_ts = hits[-1]["_source"]["timestamp"]
        total_idle_sec = hits[-1]["_source"].get("idle_duration_sec", 0)
        session_id = hits[0]["_source"]["session_id"]
        seq_num_start = hits[0]["_source"]["seq_num"]

        # 2️⃣ Determine allowed pause duration
        max_pause_sec = PAUSE_TYPES.get(requested_pause_type)
        if max_pause_sec is None:
            raise HTTPException(status_code=400, detail="Invalid pause type")
        applied_pause_sec = min(total_idle_sec, max_pause_sec)
        leftover_idle_sec = total_idle_sec - applied_pause_sec

        # 3️⃣ Delete original idle events
        es.delete_by_query(
            index="employee_activity",
            query={
                "bool": {
                    "must": [
                        {"term": {"employee_id.keyword": employee_id}},
                        {"term": {"idle_id.keyword": idle_id}}
                    ]
                }
            },
            refresh=True
        )

        # 4️⃣ Insert pause event
        pause_doc = {
            "timestamp": idle_start_ts,
            "event": "pause",
            "employee_id": employee_id,
            "session_id": session_id,
            "seq_num": seq_num_start,
            "reason": requested_pause_type,
            "duration_minutes": applied_pause_sec / 60,
            "corrected": True
        }
        es.index(index="employee_activity", document=pause_doc)

        # 5️⃣ Insert leftover idle if needed
        if leftover_idle_sec > 0:
            leftover_idle_doc = {
                "timestamp": idle_start_ts + int(applied_pause_sec * 1000),
                "event": "idle_end",
                "employee_id": employee_id,
                "session_id": session_id,
                "seq_num": seq_num_start + 1,
                "idle_id": idle_id,
                "idle_duration_sec": leftover_idle_sec,
                "corrected": True
            }
            es.index(index="employee_activity", document=leftover_idle_doc)

    return {"message": f"Request {request_id} {decision}"}
