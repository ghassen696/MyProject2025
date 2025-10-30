"""from elasticsearch import Elasticsearch
from report_pipeline import process_employee_day

es = Elasticsearch("http://localhost:9200")

# Replace with a real employee_id and date present in your ES
employee_id = "G50047910-5JjP5"
date_str = "2025-10-16"

result = process_employee_day(es, employee_id, date_str)
print("Daily Summary:\n", result.get("daily_summary"))
"""
from elasticsearch import Elasticsearch
from preprocessing import fetch_logs_for_employee, prepare_chunks_for_pipeline, save_chunks_to_elasticsearch
from classification import batch_classify_parallel,save_classifications_to_elasticsearch
from Summarization import summarize_and_store
# 🧠 Connect to your Elasticsearch instance
es = Elasticsearch("http://localhost:9200")

# 🧩 Parameters for testing
INDEX = "employee_activity"
EMPLOYEE_ID = "G50047910-5JjP5"   # your test employee ID
DATE = "2025-10-18"               # any date that exists in your data

# ⚡ Fetch logs for that employee and date
logs = fetch_logs_for_employee(es, INDEX, EMPLOYEE_ID, DATE)

print(f"Fetched {len(logs)} logs for {EMPLOYEE_ID} on {DATE}")

# 🔍 Preprocess and chunk logs
chunks = prepare_chunks_for_pipeline(logs, employee_id=EMPLOYEE_ID, date_str=DATE)
print(f"Classified {len(chunks)} chunks.")
save_chunks_to_elasticsearch(chunks ,es)
classified = batch_classify_parallel(chunks, max_workers=10)
print("classification done")
print(f"Classified {len(classified_chunks)} chunks.")
save_classifications_to_elasticsearch(classified_chunks, es)
print(f"Saved {len(classified_chunks)} classified chunks to index.")
# 🧾 Summarize
result = summarize_and_store(classified_chunks, employee_id=EMPLOYEE_ID, date=DATE)
print("✅ Daily Summary Generated:")
print(json.dumps(result, indent=2))


"""
test the best workers that can speed up the classification
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

for workers in [1, 2, 4, 6, 8, 10, 12]:
    start = time.time()
    classified = batch_classify_parallel(chunks[:2], max_workers=workers)
    print(f"{workers} workers → {time.time() - start:.2f}s")
    """
"""
this one for multi processing different employees in paralele very important
from concurrent.futures import ThreadPoolExecutor, as_completed
from preprocessing_enhanced import fetch_logs_for_employee, prepare_chunks_for_pipeline
from enhanced_classification import batch_classify_parallel, save_classifications_to_elasticsearch
from summarization import summarize_and_store
from elasticsearch import Elasticsearch

ES = Elasticsearch("http://localhost:9200")

def process_employee(employee_id: str, date: str):
    # Fetch logs
    logs = fetch_logs_for_employee(ES, "employee_logs", employee_id, date)
    if not logs:
        print(f"No logs for {employee_id} on {date}")
        return

    # Preprocess and chunk
    chunks = prepare_chunks_for_pipeline(logs, employee_id=employee_id, date_str=date)

    # Classify in parallel
    classified = batch_classify_parallel(chunks)

    # Merge classification results back to chunks
    for ch, cl in zip(chunks, classified):
        ch.update(cl)

    # Save classified chunks
    save_classifications_to_elasticsearch(chunks, ES)

    # Summarize and store daily summary
    summarize_and_store(chunks, employee_id, date)

# -------------------------
# Multi-employee parallel executor
# -------------------------
def process_employees(employee_ids: list, date: str, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_employee, eid, date): eid for eid in employee_ids}
        for future in as_completed(futures):
            eid = futures[future]
            try:
                future.result()
                print(f"Completed processing for {eid}")
            except Exception as e:
                print(f"Failed processing {eid}: {e}")
"""