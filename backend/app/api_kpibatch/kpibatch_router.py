from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_scan
from .kpibatch_services import transform_es_doc,rollup_productivity
from ..config import ELASTICSEARCH_URL, INDEX_KPIBATCH
from .models import (
    ProductivityData, HourlyValue, AppUsage, ShortcutUsed,
    TopWindow, DonutCategory
)
import json

es = AsyncElasticsearch(ELASTICSEARCH_URL)
router = APIRouter(prefix="/productivity", tags=["Productivity"])

@router.get("/", response_model=List[ProductivityData])
async def get_productivity(
    employee_id: Optional[str] = Query(None, description="Filter by employee_id"),
    date: Optional[str] = Query(None, description="Filter by date in YYYY-MM-DD format")
):
    # If no date provided, use yesterday by default
    if not date:
        yesterday = datetime.utcnow() - timedelta(days=108)
        date = yesterday.strftime("%Y-%m-%d")

    # If both employee_id and date provided, get single document
    if employee_id:
        doc_id = f"{employee_id}-{date}"
        resp = await es.get(index=INDEX_KPIBATCH, id=doc_id, ignore=[404])
        if resp.get("found"):
            return [transform_es_doc(resp)]
        # If not found, just return empty list instead of 404 to allow front-end flexibility
        return []

    # Otherwise, fetch multiple documents for the given date
    query = {
        "query": {
            "range": {
                "date": {
                    "gte": date,
                    "lte": date
                }
            }
        }
    }

  # All employees for this date
    results = []
    
    async for hit in async_scan(es, index=INDEX_KPIBATCH, query=query):
        results.append(transform_es_doc(hit))


    if not results:
        raise HTTPException(status_code=404, detail=f"No Productivity data found for {date}")

    return results

#added roolup api
@router.get("/rollup/")
async def get_productivity_rollup(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    if not start_date or not end_date:
        yesterday = datetime.utcnow() - timedelta(days=1)
        start_date = end_date = yesterday.strftime("%Y-%m-%d")

    query = {
        "query": {
            "bool": {
                "must": [
                    {"range": {"date": {"gte": start_date, "lte": end_date}}}
                ] + ([{"term": {"employee_id.keyword": employee_id}}] if employee_id else [])
            }
        }
    }

    docs = []
    async for hit in async_scan(es, index=INDEX_KPIBATCH, query=query):
        docs.append(transform_es_doc(hit))

    if not docs:
        raise HTTPException(status_code=404, detail="No data found")

    return rollup_productivity(docs)

@router.get("/employees/", response_model=List[str])
async def get_all_employee_ids():
    query = {
        "size": 0,
        "aggs": {
            "unique_ids": {
                "terms": {"field": "employee_id.keyword", "size": 10000}
            }
        }
    }

    resp = await es.search(index=INDEX_KPIBATCH, body=query)
    return [bucket["key"] for bucket in resp["aggregations"]["unique_ids"]["buckets"]]

"""dzd"""
"""from statistics import mean
from collections import defaultdict
from datetime import datetime

def aggregate_productivity_data(docs: List[ProductivityData]) -> ProductivityData:
    if not docs:
        raise ValueError("No documents to aggregate")

    worked_days = len(docs)  # Only count days with data

    # Helper to safely average
    def avg(values): 
        return sum(values) / worked_days if values else 0
    def sum_values(values): return sum(values) if values else 0

    employee_id = docs[0].employee_id
    date_range = f"{docs[0].date} to {docs[-1].date}"

    # --- Numeric aggregates ---
    total_keystrokes = sum_values([d.total_keystrokes for d in docs])
    avg_keystrokes = total_keystrokes / worked_days
    active_min = sum_values([d.active_min for d in docs])
    avg_active_min = active_min / worked_days

    idle_min = sum_values([d.idle_min for d in docs])
    avg_idle_min = idle_min / worked_days

    pause_min = sum_values([d.pause_min for d in docs])
    avg_pause_min = pause_min / worked_days

    productivity_score = avg([d.productivity_score for d in docs])
    focus_ratio = avg([d.focus_ratio for d in docs])
    shortcut_count = sum_values([d.shortcut_count for d in docs])
    heartbeat_count = sum_values([d.heartbeat_count for d in docs])
    unique_apps_count = sum_values([d.unique_apps_count for d in docs])
    #unique_apps_count = len(set(a.app_name for d in docs for a in d.active_per_app))
    distinct_event_types = avg([d.distinct_event_types for d in docs])
    active_events = sum_values([d.active_events for d in docs])

    # --- Per-hour cumulative data ---
    def merge_hourly(lists):
        agg = defaultdict(float)
        for d in lists:
            for h in d:
                agg[h.hour] += h.value
        return [HourlyValue(hour=h, value=v) for h, v in sorted(agg.items())]

    typing_per_hour = merge_hourly([d.typing_per_hour for d in docs])
    keystrokes_per_active_hour = merge_hourly([d.keystrokes_per_active_hour for d in docs])
    idle_per_hour = merge_hourly([d.idle_per_hour for d in docs])

    # --- App usage ---
    app_idle_agg = defaultdict(float)
    for d in docs:
        for app in d.idle_per_app:
            app_idle_agg[app.app_name] += app.value
    total_idle = sum(app_idle_agg.values())
    idle_per_app = [
        AppUsage(app_name=k, value=v, percentage=(v / total_idle * 100 if total_idle else 0))
        for k, v in app_idle_agg.items()
    ]

    # --- Active per app ---
    app_active_agg = defaultdict(float)
    for d in docs:
        for app in d.active_per_app:
            app_active_agg[app.app_name] += app.value
    total_active = sum(app_active_agg.values())
    active_per_app = [
        AppUsage(app_name=k, value=v, percentage=(v / total_active * 100 if total_active else 0))
        for k, v in app_active_agg.items()
    ]

    # --- Shortcuts cumulative ---
    shortcuts_used = []
    shortcut_counter = defaultdict(int)
    for d in docs:
        for s in d.shortcuts_used:
            shortcut_counter[s.shortcut] += s.count
    for k, v in shortcut_counter.items():
        shortcuts_used.append(ShortcutUsed(shortcut=k, count=v))

    # --- Sessions merged ---
    sessions = [s for d in docs for s in d.sessions]

    # --- Top windows (sum switch_count, sum time_spent) ---
    window_agg = defaultdict(lambda: {"switch_count": 0, "time_spent": 0})
    for d in docs:
        for w in d.top_windows:
            window_agg[w.window_title]["switch_count"] += w.switch_count
            window_agg[w.window_title]["time_spent"] += w.time_spent or 0
    top_windows = [
        TopWindow(window_title=k, switch_count=v["switch_count"], time_spent=v["time_spent"])
        for k, v in window_agg.items()
    ]

    # --- Donut chart cumulative ---
    donut_agg = defaultdict(int)
    for d in docs:
        for c in d.donut_chart:
            donut_agg[c.category] += c.count
    donut_chart = [DonutCategory(category=k, count=v) for k, v in donut_agg.items()]

    return ProductivityData(
        employee_id=employee_id,
        date=date_range,
        total_keystrokes=total_keystrokes,
        active_min=active_min,
        idle_min=idle_min,
        pause_min=pause_min,
        productivity_score=productivity_score,
        focus_ratio=focus_ratio,
        shortcut_count=shortcut_count,
        heartbeat_count=heartbeat_count,

        typing_per_hour=typing_per_hour,
        keystrokes_per_active_hour=keystrokes_per_active_hour,
        idle_per_hour=idle_per_hour,
        idle_per_app=idle_per_app,
        pause_per_hour=[],  # can extend if needed
        pause_total_min=0,
        avg_pause_duration_min=0,

        shortcuts_used=shortcuts_used,
        shortcuts_per_hour=[],  # optional
        active_per_app=active_per_app,
        app_usage_per_hour=[],
        top_windows=top_windows,
        window_switch_count=sum([d.window_switch_count for d in docs]),
        context_switch_rate=avg([d.context_switch_rate for d in docs]),
        sessions=sessions,
        unique_apps_count=unique_apps_count,
        distinct_event_types=int(distinct_event_types),
        active_events=active_events,
        donut_chart=donut_chart
    )


@router.get("/range", response_model=ProductivityData)
async def get_productivity_range(
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date = datetime.today().date()

    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end_date = start_date

    # Convert to string for ES (with time range for full days)
    start_date_str = f"{start_date}T00:00:00"
    end_date_str = f"{end_date}T23:59:59"

    print("FROM:", start_date_str, "TO:", end_date_str)
    # Elasticsearch range query
    
    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"employee_id.keyword": employee_id}},
                    {
                        "range": {
                            "date": {
                                "gte": start_date_str,
                                "lte": end_date_str
                            }
                        }
                    }
                ]
            }
        }
    }

    results = []
    print("FINAL QUERY:", json.dumps(query, indent=2))

    async for hit in async_scan(es, index=INDEX_KPIBATCH, query=query):
        results.append(transform_es_doc(hit))

    if not results:
        raise HTTPException(status_code=404, detail=f"No data for {employee_id} between {from_date} and {to_date}")

    # Aggregate results into one summary
    aggregated = aggregate_productivity_data(results)
    return aggregated
"""