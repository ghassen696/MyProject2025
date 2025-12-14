# unified_pipeline.py
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from elasticsearch import Elasticsearch
from preprocessing import fetch_logs_for_employee, prepare_chunks_for_pipeline
from classification import batch_classify_parallel, save_classifications_to_elasticsearch
from Summarization import summarize_and_store
import json
import os
ES = Elasticsearch("http://193.95.30.190:9200")

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
    print(f"[{employee_id}] 🔄 Preprocessing logs into chunks...")
    chunks = prepare_chunks_for_pipeline(logs, employee_id=employee_id, date_str=date,min_quality_score=0.65)
    if not chunks:
        print(f"[{employee_id}] No chunks created. Skipping...")
        return
    # ADD THIS DIAGNOSTIC BLOCK:
    print(f"\n{'='*60}")
    print(f"PRE-CLASSIFICATION DIAGNOSTICS - {employee_id}")
    print(f"{'='*60}")
    print(f"Total chunks after preprocessing: {len(chunks)}")

    # Analyze chunk quality distribution
    quality_scores = [c.get("meta", {}).get("quality", {}).get("quality_score", 0) for c in chunks]
    print(f"Quality scores: min={min(quality_scores):.2f}, max={max(quality_scores):.2f}, avg={sum(quality_scores)/len(quality_scores):.2f}")

    # Analyze chunk durations
    durations = []
    for c in chunks:
        try:
            from datetime import datetime
            start = datetime.fromisoformat(c["start_time"])
            end = datetime.fromisoformat(c["end_time"])
            durations.append((end - start).total_seconds() / 60)
        except:
            pass

    if durations:
        print(f"Chunk durations (min): min={min(durations):.1f}, max={max(durations):.1f}, avg={sum(durations)/len(durations):.1f}")

    print(f"Event counts per chunk: min={min([c.get('meta',{}).get('original_event_count',0) for c in chunks])}, "
        f"max={max([c.get('meta',{}).get('original_event_count',0) for c in chunks])}")
    print(f"{'='*60}\n")

    # Original line continues:
    print(f"[{employee_id}] Created {len(chunks)} chunks.")
    #chunks = chunks[:2]
    # 3️⃣ Classify chunks in parallel
    classified = batch_classify_parallel(chunks, max_workers=chunk_workers)
    # ADD THIS DIAGNOSTIC BLOCK:
    print(f"\n{'='*60}")
    print(f"POST-CLASSIFICATION DIAGNOSTICS - {employee_id}")
    print(f"{'='*60}")
    print(f"Total classified chunks: {len(classified)}")

    categories = {}
    for c in classified:
        cat = c.get("category", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\nCategory distribution:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    high_conf = [c for c in classified if c.get("confidence", 0) >= 0.4]
    not_unknown = [c for c in high_conf if c.get("category") != "Unknown"]

    print(f"\nFiltering check:")
    print(f"  Chunks with confidence >= 0.4: {len(high_conf)}")
    print(f"  Chunks with known category: {len(not_unknown)}")
    print(f"  Will be sent to summarization: {len(not_unknown)}")
    print(f"{'='*60}\n")

    # Original line continues:
    print(f"[{employee_id}] Classification completed.")    
    # 4️⃣ Save classified chunks to Elasticsearch
    save_classifications_to_elasticsearch(classified, ES)
    print(f"[{employee_id}] Classified chunks saved.")

    # 5️⃣ Summarize daily activity
    summarize_and_store(classified, employee_id, date)
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
    date_to_process = "2025-11-20"
    process_employees(employees, date_to_process, employee_workers=1, chunk_workers=8)
