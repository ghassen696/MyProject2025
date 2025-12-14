"""from elasticsearch import Elasticsearch
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
    if not text:
        return []
    return embedding_model.encode(text, convert_to_numpy=True).tolist()

def search_similar_chunks(task_description: str, start_date=None, end_date=None, top_k: int = TOP_K):

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
    start_of_week = today - datetime.timedelta(days=70)
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
"""
from datetime import date, timedelta
from collections import defaultdict
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer

# -------------------------
# Elasticsearch & Embeddings
# -------------------------
es = Elasticsearch("http://193.95.30.190:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
INDEX_NAME = "employee_classifications"
KPI_INDEX = "employee_kpi_summary4"

# -------------------------
# Helper Functions
# -------------------------
def embed_task(task_description: str) -> list:
    """Generate embedding for the task description."""
    if not task_description:
        return []
    return embedding_model.encode(task_description, convert_to_numpy=True).tolist()

def search_chunks(task_embedding: list, start_date=None, end_date=None, 
                  employee_id=None, top_k: int = 50):
    """Search for top matching chunks using cosine similarity, with optional filters."""
    
    # Base query with script_score
    query = {
        "size": top_k,
        "query": {
            "bool": {
                "must": [
                    {
                        "script_score": {
                            "query": {"match_all": {}},  # always match all
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'summary_vector') + 1.0",
                                "params": {"query_vector": task_embedding}
                            }
                        }
                    }
                ],
                "filter": []  # filters will be appended here
            }
        }
    }

    # Apply optional date filter
    if start_date and end_date:
        query["query"]["bool"]["filter"].append({
            "range": {"start_time": {"gte": start_date, "lte": end_date}}}
        )

    # Apply optional employee filter
    if employee_id:
        query["query"]["bool"]["filter"].append({
            "term": {"employee_id": employee_id}}
        )

    # Execute search
    res = es.search(index=INDEX_NAME, body=query)
    print("Hits found:", len(res["hits"]["hits"]))

    # Process hits
    chunks = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        chunks.append({
            "chunk_id": src.get("chunk_id"),
            "employee_id": src.get("employee_id"),
            "category": src.get("category"),
            "confidence": src.get("confidence"),
            "rationale": src.get("rationale"),
            "similarity": hit["_score"] - 1.0,  # remove the +1 offset
            "summary_text": src.get("summary_text", ""),
            "start_time": src.get("start_time"),
            "end_time": src.get("end_time")
        })
    return chunks

def calculate_task_coverage(chunks, threshold=0.6):
    """Calculate coverage metrics for a list of chunks."""
    if not chunks:
        return {"coverage_score":0,"evidence_strength":"none","high_match_count":0,"total_chunks":0}
    
    high_matches = [c for c in chunks if c["similarity"] >= threshold]
    avg_similarity = sum(c["similarity"] for c in chunks)/len(chunks)
    
    if avg_similarity >= 0.7 and len(high_matches) >= 3:
        strength = "strong"
    elif avg_similarity >= 0.5 and len(high_matches) >= 2:
        strength = "moderate"
    elif avg_similarity >= 0.3:
        strength = "weak"
    else:
        strength = "minimal"
    
    return {
        "coverage_score": round(avg_similarity, 3),
        "evidence_strength": strength,
        "high_match_count": len(high_matches),
        "total_chunks": len(chunks)
    }

# -------------------------
# Test Script
# -------------------------
if __name__ == "__main__":
    task_description = "Fix login authentication bug"
    today = date.today()
    start_date = (today - timedelta(days=70)).isoformat()
    end_date = today.isoformat()

    # 1️⃣ Generate embedding
    embedding = embed_task(task_description)
    print("Embedding length:", len(embedding))  # should be 768

    # 2️⃣ Search chunks
    chunks = search_chunks(task_embedding=embedding, start_date=start_date, end_date=end_date)
    print("Chunks found:", len(chunks))
    for c in chunks[:3]:
        print(c)

    # 3️⃣ Calculate coverage
    coverage = calculate_task_coverage(chunks)
    print("Coverage:", coverage)
