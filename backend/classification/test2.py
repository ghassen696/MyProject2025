# unified_pipeline.py
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from elasticsearch import Elasticsearch
from preprocessing import fetch_logs_for_employee, prepare_chunks_for_pipeline
from classification import batch_classify_parallel, save_classifications_to_elasticsearch
from Summarization import summarize_and_store

ES = Elasticsearch("http://localhost:9200")

# -------------------------
# Process a single employee
# -------------------------
def process_employee(employee_id: str, date: str, chunk_workers: int = 8):
    start_time = time.time()
    print(f"[{employee_id}] Starting pipeline for {date}...")

    # 1️⃣ Fetch logs
    logs = fetch_logs_for_employee(ES, "employee_activity", employee_id, date)
    if not logs:
        print(f"[{employee_id}] No logs found for {date}. Skipping...")
        return
    print(f"[{employee_id}] Fetched {len(logs)} logs.")

    # 2️⃣ Preprocess and create chunks
    chunks = prepare_chunks_for_pipeline(logs, employee_id=employee_id, date_str=date)
    if not chunks:
        print(f"[{employee_id}] No chunks created. Skipping...")
        return
    print(f"[{employee_id}] Created {len(chunks)} chunks.")
    chunks = chunks[:2]
    # 3️⃣ Classify chunks in parallel
    classified = batch_classify_parallel(chunks, max_workers=chunk_workers)
    print(f"[{employee_id}] Classification completed.")

    # 4️⃣ Save classified chunks to Elasticsearch
    save_classifications_to_elasticsearch(classified, ES)
    print(f"[{employee_id}] Classified chunks saved.")

    # 5️⃣ Summarize daily activity
    summarize_and_store(chunks, employee_id, date)
    print(f"[{employee_id}] Daily summary saved.")

    end_time = time.time()
    print(f"[{employee_id}] Pipeline finished in {round(end_time - start_time, 2)}s.\n")

# -------------------------
# Multi-employee executor
# -------------------------
def process_employees(employee_ids: list, date: str, employee_workers: int = 2, chunk_workers: int = 6):
    print(f"Starting multi-employee pipeline for {len(employee_ids)} employees on {date}...")
    with ThreadPoolExecutor(max_workers=employee_workers) as executor:
        futures = {
            executor.submit(process_employee, eid, date, chunk_workers): eid for eid in employee_ids
        }
        for future in as_completed(futures):
            eid = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[{eid}] Pipeline failed: {e}")
    print("All employees processed.")

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    employees = ["G50047910-5JjP5"]  # add your employee IDs
    date_to_process = "2025-10-21"
    process_employees(employees, date_to_process, employee_workers=3, chunk_workers=10)
