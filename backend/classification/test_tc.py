from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import json
import datetime

# ---------------------------------
# Configuration
# ---------------------------------
ES_URL = "http://localhost:9200"
INDEX_NAME = "employee_classifications"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
TOP_K = 5  # Number of top matches per task

# Connect to Elasticsearch
es = Elasticsearch(ES_URL)

# Load embedding model
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

def embed_text(text: str):
    """Generate embedding for a given text."""
    if not text:
        return []
    return embedding_model.encode(text, convert_to_numpy=True).tolist()

def search_similar_chunks(task_description: str, start_date=None, end_date=None, top_k: int = TOP_K):
    """
    Search for similar chunks for a given task, optionally filtered by date range.
    """
    print(f"\n[🔍] Searching for task similarity: {task_description}")
    query_vector = embed_text(task_description)

    # Build the base query
    query = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {"script_score": {
                        "query": {"match_all": {}},
                        "script": {
                            "source": "cosineSimilarity(params.query_vector, 'summary_vector') + 1.0",
                            "params": {"query_vector": query_vector}
                        }
                    }}
                ]
            }
        }
    }

    # Apply optional date filter
    if start_date and end_date:
        query["query"]["bool"]["filter"] = [{
            "range": {
                "start_time": {
                    "gte": start_date,
                    "lte": end_date
                }
            }
        }]

    # Execute search
    res = es.search(index=INDEX_NAME, body=query)
    results = []

    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        score = hit["_score"] - 1.0  # remove the +1 offset
        results.append({
            "employee_id": src.get("employee_id"),
            "chunk_id": src.get("chunk_id"),
            "category": src.get("category"),
            "confidence": src.get("confidence"),
            "similarity": round(score, 3),
            "summary_text": src.get("summary_text", "")[:150] + "..."
        })

    return results

# ---------------------------------
# Run multiple task queries
# ---------------------------------
if __name__ == "__main__":
    # Example: Admin inputs multiple tasks
    admin_tasks = [
        "work on automation tasks and employee_chunks index and test python code preprocessing "
    ]

    # Admin chooses a date range
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=7)
    start_date = start_of_week.isoformat()
    end_date = today.isoformat()

    print(f"\n[🗓️] Searching chunks between {start_date} and {end_date}")

    # Process each task
    for task in admin_tasks:
        matches = search_similar_chunks(task, start_date=start_date, end_date=end_date)
        print(f"\n[✅] Top matches for task: {task}")
        for i, match in enumerate(matches, 1):
            print(f"{i}. Employee: {match['employee_id']}, Category: {match['category']}, Similarity: {match['similarity']}")
            print(f"   Summary: {match['summary_text']}\n")
