"""from elasticsearch import Elasticsearch
from Summarization import summarize_and_store

ES = Elasticsearch("http://193.95.30.190:9200")
INDEX = "employee_classifications"

def fetch_classified_chunks(employee_id: str, date: str):

    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"employee_id": employee_id}},
                    {"range": {"start_time": {"gte": f"{date}T00:00:00", "lt": f"{date}T23:59:59"}}}
                ]
            }
        },
        "size": 1000,
        "sort": [{"chunk_id": {"order": "asc"}}]
    }
    res = ES.search(index=INDEX, body=query)
    hits = res.get("hits", {}).get("hits", [])
    chunks = [hit["_source"] for hit in hits]
    print(f"[{employee_id}] Fetched {len(chunks)} chunks for {date}.")
    return chunks

if __name__ == "__main__":
    employee_id = "G50047910-5JjP5"
    date = "2025-10-21"

    chunks = fetch_classified_chunks(employee_id, date)
    if chunks:
        try:
            summary = summarize_and_store(chunks, employee_id, date)
            print("[Done] Summary generated and saved.")
        except Exception as e:
            print(f"[{employee_id}] ❌ Pipeline failed: {e}")
            traceback.print_exc()
    else:
        print("No classified chunks found.")
"""
"""
from elasticsearch import Elasticsearch

ES = Elasticsearch("http://localhost:9200")
index_name = "employee_classifications"

# Check if index exists first
if ES.indices.exists(index=index_name):
    ES.indices.delete(index=index_name)
    print(f"Index '{index_name}' deleted successfully.")
else:
    print(f"Index '{index_name}' does not exist.")
"""
"""
from elasticsearch import Elasticsearch
import json
import os

# --- Configuration ---
ES = Elasticsearch("http://localhost:9200")
index_name = "employee_classifications"
target_date = "2025-10-28"
size_limit = 50

# --- Output Setup ---
os.makedirs("output", exist_ok=True)
output_file = f"output/{index_name}_{target_date}.json"

# --- Query ---
query = {
    "range": {
        "start_time": {
            "gte": f"{target_date}T00:00:00",
            "lte": f"{target_date}T23:59:59"
        }
    }
}

# --- Search Request ---
response = ES.search(
    index=index_name,
    size=size_limit,
    query=query,
    sort=[{"start_time": {"order": "asc"}}]  # optional, chronological order
)

docs = [hit["_source"] for hit in response["hits"]["hits"]]

# --- Save to File ---
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(docs, f, ensure_ascii=False, indent=4)

print(f"✅ Saved {len(docs)} documents from {index_name} (date={target_date}) to {output_file}")
"""
from elasticsearch import Elasticsearch
from datetime import date
ES = Elasticsearch("http://193.95.30.190:9200")
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
if __name__ == "__main__":
    INDEX = "employee_activity"

    print("\n🔍 Fetching ALL employees from Elasticsearch...\n")
    employees = get_all_employee_ids(ES, INDEX)
    
    print(f"👥 Found {len(employees)} employees:")
    for eid in employees:
        print("  -", eid)
    target_date = date.today().strftime("%Y-%m-%d")
    print(f"\n📅 Processing date: {target_date}\n")