from elasticsearch import Elasticsearch
from Summarization import summarize_and_store

ES = Elasticsearch("http://localhost:9200")
INDEX = "employee_classifications"

def fetch_classified_chunks(employee_id: str, date: str):
    """Fetch all classified chunks for a given employee and date."""
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
