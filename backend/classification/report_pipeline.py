import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from elasticsearch import Elasticsearch
from typing import List, Dict, Any, Optional

# --- Your modules ---
from preprocessing import fetch_logs_for_employee, adaptive_chunk_logs, normalize_date
from classification import batch_classify
from Summarization import summarize_and_store
from elastic_utils import save_daily_report, save_classifications, save_summaries, save_work_patterns

MAX_WORKERS = 4  # concurrency limit

# -------------------------
# Employee / Day helpers
# -------------------------
def get_unique_employee_ids(es: Elasticsearch, index: str = "employee_activity") -> List[str]:
    """Fetch all unique employee IDs from activity index."""
    body = {
        "size": 0,
        "aggs": {"unique_employees": {"terms": {"field": "employee_id.keyword", "size": 10000}}}
    }
    resp = es.search(index=index, body=body)
    return [bucket["key"] for bucket in resp["aggregations"]["unique_employees"]["buckets"]]

def get_employee_days(es: Elasticsearch, employee_id: str, index: str = "employee_activity") -> List[str]:
    """Fetch all active days for an employee."""
    body = {
        "size": 0,
        "query": {"term": {"employee_id.keyword": employee_id}},
        "aggs": {"active_days": {"date_histogram": {"field": "timestamp", "calendar_interval": "day"}}}
    }
    resp = es.search(index=index, body=body)
    return [bucket["key_as_string"][:10] for bucket in resp["aggregations"]["active_days"]["buckets"]]

# -------------------------
# Employee day processing
# -------------------------
def process_employee_day(es: Elasticsearch, employee_id: str, date_str: str) -> Optional[Dict[str, Any]]:
    """Full pipeline for one employee on one day."""
    try:
        # 1️⃣ Fetch logs
        logs = fetch_logs_for_employee(es, "employee_activity", employee_id, date_str)
        if not logs:
            print(f"⚠️ No logs for {employee_id} on {date_str}")
            return None

        # 2️⃣ Chunk logs
        chunks = adaptive_chunk_logs(logs)
        if not chunks:
            print(f"⚠️ No valid chunks for {employee_id} on {date_str}")
            return None

        # 3️⃣ Prepare text for classification
        for ch in chunks:
            ch_text = " ".join([e["description"] for e in ch])
            ch["text"] = ch_text

        # 4️⃣ Classify chunks
        classified_chunks = batch_classify([{"text": ch["text"]} for ch in chunks])

        # 5️⃣ Summarize full day
        summary = summarize_and_store(classified_chunks, employee_id, date_str)

        # 6️⃣ Save outputs to ES
        save_daily_report(es, employee_id, date_str, {
            "employee_id": employee_id,
            "daily_summary": summary.get("summary", ""),
            "work_patterns": {"chunk_count": len(chunks), "classifications": classified_chunks},
            "chunk_summaries": summary.get("activities", [])
        })
        save_classifications(es, employee_id, date_str, classified_chunks, chunks)
        save_summaries(es, employee_id, date_str, classified_chunks, chunks)
        save_work_patterns(es, employee_id, date_str, {"chunk_count": len(chunks), "classifications": classified_chunks})

        print(f"✅ Processed {employee_id} on {date_str}")
        return {"employee_id": employee_id, "date": date_str, "summary": summary.get("summary"), "chunk_count": len(chunks)}

    except Exception as e:
        print(f"❌ Failed to process {employee_id} on {date_str}: {e}")
        return None

# -------------------------
# Batch processing
# -------------------------
def process_all_employees(es: Elasticsearch, max_workers: int = MAX_WORKERS):
    """Process all employees concurrently."""
    employee_ids = get_unique_employee_ids(es)
    print(f"🏭 Found {len(employee_ids)} employees to process")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for emp_id in employee_ids:
            days = get_employee_days(es, emp_id)
            for day in days:
                future = executor.submit(process_employee_day, es, emp_id, day)
                future_map[future] = (emp_id, day)

        for future in as_completed(future_map):
            emp_id, day = future_map[future]
            res = future.result()
            if res:
                results.append(res)

    print(f"🎉 Batch processing complete: {len(results)} day-reports generated")
    return results

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    es = Elasticsearch("http://localhost:9200")  # adjust if needed
    process_all_employees(es)
