#report_pipeline.py
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from elasticsearch import Elasticsearch
from preprocessing import fetch_logs_for_employee, prepare_chunks_for_pipeline
from classification import batch_classify_parallel, save_classifications_to_elasticsearch
from Summarization import summarize_and_store

ES = Elasticsearch("http://193.95.30.190:9200")

# -------------------------
# Process a single employee
# -------------------------
def process_employee(employee_id: str, date: str, chunk_workers: int = 8):
    start_time = time.time()
    print(f"\n{'='*80}")
    print(f"[{employee_id}] STARTING PIPELINE FOR {date}")
    print(f"{'='*80}\n")

    # 1️⃣ Fetch logs
    print(f"[{employee_id}] 📥 Fetching logs from Elasticsearch...")
    logs = fetch_logs_for_employee(ES, "employee_activity", employee_id, date)
    if not logs:
        print(f"[{employee_id}] ⚠️ No logs found for {date}. Skipping...")
        return
    print(f"[{employee_id}] ✅ Fetched {len(logs)} raw logs.\n")

    # 2️⃣ Preprocess and create chunks
    print(f"[{employee_id}] 🔄 Preprocessing logs into chunks...")
    chunks = prepare_chunks_for_pipeline(
        logs, 
        employee_id=employee_id, 
        date_str=date,
        min_quality_score=0.65  # High quality threshold
    )
    
    if not chunks:
        print(f"[{employee_id}] ⚠️ No chunks created after filtering. Skipping...")
        return

    # DIAGNOSTIC: Chunk analysis
    print(f"\n{'='*60}")
    print(f"PREPROCESSING DIAGNOSTICS - {employee_id}")
    print(f"{'='*60}")
    print(f"Total chunks created: {len(chunks)}")
    
    quality_scores = [c.get("meta", {}).get("quality", {}).get("quality_score", 0) for c in chunks]
    print(f"Quality scores: min={min(quality_scores):.2f}, max={max(quality_scores):.2f}, avg={sum(quality_scores)/len(quality_scores):.2f}")
    
    durations = []
    for c in chunks:
        try:
            start_dt = datetime.fromisoformat(c["start_time"])
            end_dt = datetime.fromisoformat(c["end_time"])
            durations.append((end_dt - start_dt).total_seconds() / 60)
        except:
            pass
    
    if durations:
        print(f"Chunk durations (minutes): min={min(durations):.1f}, max={max(durations):.1f}, avg={sum(durations)/len(durations):.1f}")
    
    event_counts = [c.get('meta', {}).get('original_event_count', 0) for c in chunks]
    print(f"Events per chunk: min={min(event_counts)}, max={max(event_counts)}, avg={sum(event_counts)/len(event_counts):.1f}")
    print(f"{'='*60}\n")

    # 3️⃣ Classify chunks in parallel
    print(f"[{employee_id}] 🤖 Starting parallel classification...")
    classified = batch_classify_parallel(chunks, max_workers=chunk_workers)
    
    # DIAGNOSTIC: Classification analysis
    print(f"\n{'='*60}")
    print(f"CLASSIFICATION DIAGNOSTICS - {employee_id}")
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
    
    print(f"\nSummarization eligibility:")
    print(f"  Chunks with confidence >= 0.4: {len(high_conf)}/{len(classified)}")
    print(f"  Chunks with known category: {len(not_unknown)}/{len(high_conf)}")
    print(f"  Chunks that will be summarized: {len(not_unknown)}")
    print(f"{'='*60}\n")
    
    print(f"[{employee_id}] ✅ Classification completed.\n")

    # 4️⃣ Save classified chunks to Elasticsearch
    print(f"[{employee_id}] 💾 Saving classified chunks to Elasticsearch...")
    save_classifications_to_elasticsearch(classified, ES)
    print(f"[{employee_id}] ✅ Classified chunks saved.\n")

    # 5️⃣ Summarize daily activity
    print(f"[{employee_id}] 📊 Starting daily summarization...")
    summarize_and_store(classified, employee_id, date)  # ✅ FIXED: Use classified chunks
    
    end_time = time.time()
    elapsed = end_time - start_time
    print(f"\n{'='*80}")
    print(f"[{employee_id}] ✅ PIPELINE COMPLETED IN {elapsed:.2f}s ({elapsed/60:.1f} minutes)")
    print(f"{'='*80}\n")

# -------------------------
# Multi-employee executor
# -------------------------
def process_employees(employee_ids: list, date: str, employee_workers: int = 2, chunk_workers: int = 6):
    print(f"\n{'#'*80}")
    print(f"MULTI-EMPLOYEE PIPELINE")
    print(f"Employees: {len(employee_ids)} | Date: {date}")
    print(f"Parallelization: {employee_workers} employees, {chunk_workers} chunks per employee")
    print(f"{'#'*80}\n")
    
    pipeline_start = time.time()
    
    with ThreadPoolExecutor(max_workers=employee_workers) as executor:
        futures = {
            executor.submit(process_employee, eid, date, chunk_workers): eid 
            for eid in employee_ids
        }
        
        completed = 0
        for future in as_completed(futures):
            eid = futures[future]
            completed += 1
            try:
                future.result()
                print(f"✅ [{completed}/{len(employee_ids)}] {eid} completed successfully")
            except Exception as e:
                print(f"❌ [{completed}/{len(employee_ids)}] {eid} FAILED: {e}")
                import traceback
                traceback.print_exc()
    
    pipeline_end = time.time()
    total_time = pipeline_end - pipeline_start
    
    print(f"\n{'#'*80}")
    print(f"ALL EMPLOYEES PROCESSED")
    print(f"Total time: {total_time:.2f}s ({total_time/60:.1f} minutes)")
    print(f"Average per employee: {total_time/len(employee_ids):.2f}s")
    print(f"{'#'*80}\n")

def get_all_employee_ids(es: Elasticsearch, index_name: str):
    query = {
        "size": 0,
        "aggs": {
            "unique_ids": {
                "terms": {
                    "field": "employee_id.keyword",
                    "size": 10000
                }
            }
        }
    }

    res = es.search(index=index_name, body=query)
    return [b["key"] for b in res["aggregations"]["unique_ids"]["buckets"]]

# -------------------------
# Example usage
# -------------------------
if __name__ == "__main__":
    INDEX = "employee_activity"
    #employees = ["G50047910-5JjP5"]  # Add your employee IDs after 25
    target_date = "2025-11-25"
    #date_to_process = datetime.now().strftime("%Y-%m-%d")
    
    print("\n🔍 Fetching ALL employees from Elasticsearch...\n")
    employees = get_all_employee_ids(ES, INDEX)
    
    print(f"👥 Found {len(employees)} employees:")
    for eid in employees:
        print("  -", eid)
    #target_date = date.today().strftime("%Y-%m-%d")
    print(f"\n📅 Processing date: {target_date}\n")
    
    process_employees(
        employees, 
        target_date, 
        employee_workers=1,  # Process 1 employee at a time for debugging
        chunk_workers=8      # Parallelize chunk classification
    )