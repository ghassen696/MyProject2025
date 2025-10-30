from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict
import datetime
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from collections import defaultdict

router = APIRouter(tags=["Task Matcher"])

# -------------------------
# Elasticsearch & Embeddings
# -------------------------
es = Elasticsearch("http://localhost:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
INDEX_NAME = "employee_classifications"

# -------------------------
# Helper Functions
# -------------------------
def embed_task(task_description: str) -> list:
    """Generate embedding for the task description."""
    if not task_description:
        return []
    return embedding_model.encode(task_description, convert_to_numpy=True).tolist()

def search_chunks(task_embedding: list, start_date=None, end_date=None, top_k: int = 50) -> List[Dict]:
    """
    Retrieve top matching chunks for the task, optionally filtered by date.
    Returns all matching chunks, to be aggregated per employee later.
    """
    bool_query = {"match_all": {}}
    if start_date and end_date:
        bool_query = {
            "bool": {
                "filter": [
                    {"range": {"start_time": {"gte": start_date, "lte": end_date}}}
                ]
            }
        }

    query = {
        "size": top_k,
        "query": {
            "script_score": {
                "query": bool_query,
                "script": {
                    "source": "cosineSimilarity(params.query_vector, 'summary_vector') + 1.0",
                    "params": {"query_vector": task_embedding}
                }
            }
        }
    }

    res = es.search(index=INDEX_NAME, body=query)
    chunks = []
    for hit in res['hits']['hits']:
        src = hit['_source']
        chunks.append({
            "chunk_id": src['chunk_id'],
            "employee_id": src['employee_id'],
            "category": src['category'],
            "confidence": src['confidence'],
            "rationale": src['rationale'],
            "similarity": hit['_score'] - 1.0,
            "summary_text": src['summary_text']
        })
    return chunks

# -------------------------
# Request Schema
# -------------------------
class TaskQuery(BaseModel):
    task_description: str
    start_date: str = None
    end_date: str = None
    top_chunks_per_employee: int = 5

# -------------------------
# API Endpoint
# -------------------------
@router.post("/search")
async def search_tasks(request: TaskQuery):
    # Default to last 7 days if no dates provided
    today = datetime.date.today()
    if not request.start_date or not request.end_date:
        start_of_week = today - datetime.timedelta(days=7)
        start_date = start_of_week.isoformat()
        end_date = today.isoformat()
    else:
        start_date = request.start_date
        end_date = request.end_date

    # Generate embedding
    task_embedding = embed_task(request.task_description)

    # Get matching chunks
    chunks = search_chunks(task_embedding, start_date=start_date, end_date=end_date, top_k=200)

    # Aggregate by employee
    employee_dict = defaultdict(list)
    for chunk in chunks:
        employee_dict[chunk['employee_id']].append(chunk)

    employee_results = []
    for emp_id, emp_chunks in employee_dict.items():
        # Sort chunks by similarity descending
        emp_chunks_sorted = sorted(emp_chunks, key=lambda x: x['similarity'], reverse=True)
        top_chunks = emp_chunks_sorted[:request.top_chunks_per_employee]
        avg_similarity = sum(c['similarity'] for c in top_chunks) / len(top_chunks)
        employee_results.append({
            "employee_id": emp_id,
            "avg_similarity": round(avg_similarity, 3),
            "top_chunks": [
                {
                    "chunk_id": c["chunk_id"],
                    "similarity": round(c["similarity"], 3),
                    "rationale": c["rationale"]
                }
                for c in top_chunks
            ]
        })

    # Sort employees by average similarity descending
    employee_results = sorted(employee_results, key=lambda x: x['avg_similarity'], reverse=True)

    return {
        "task": request.task_description,
        "employee_matches": employee_results
    }

@router.get("/")
async def root():
    return {"message": "Task Similarity API is running"}
