from app.config import ELASTICSEARCH_URL ,INDEX_KPI
from datetime import datetime, timezone
from elasticsearch import AsyncElasticsearch


es = AsyncElasticsearch(ELASTICSEARCH_URL)

def get_today_timestamp():
    # midnight UTC timestamp in ms
    now = datetime.now(timezone.utc)
    today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return int(today.timestamp() * 1000)



async def get_today_kpi(employee_id=None, status=None, size=50):
    must_filters = []
    if employee_id:
        must_filters.append({"term": {"employee_id.keyword": employee_id}})
    if status:
        must_filters.append({"term": {"employee_status.keyword": status}})

    query = {
        "size": size,
        "query": {"bool": {"must": must_filters}} if must_filters else {"match_all": {}},
        "sort": [{"last_event_time": {"order": "desc"}}],
        "collapse": {"field": "employee_id.keyword"}  # ensures 1 doc per employee
    }

    resp = await es.search(index=INDEX_KPI, body=query)
    return [hit["_source"] for hit in resp["hits"]["hits"]]

"""async def get_today_kpi(employee_id=None, status=None, size=50, date=None):
    #timestamp = date or get_today_timestamp()
    timestamp = get_today_timestamp()
    #today_str = datetime.now().strftime("%Y-%m-%d")

    must_filters = [
        {"term": {"date": timestamp}}
    ]

    if employee_id:
        must_filters.append({"term": {"employee_id.keyword": employee_id}})
    if status:
        must_filters.append({"term": {"employee_status.keyword": status}})

    query = {
        "size": size,
        "query": {"bool": {"must": must_filters}},
        "sort": [{"last_event_time": {"order": "desc"}}]  # Get most recent data first

    }

    resp = await es.search(
        index=INDEX_KPI, 
        body=query,
    )
    
    return [hit["_source"] for hit in resp["hits"]["hits"]]
"""