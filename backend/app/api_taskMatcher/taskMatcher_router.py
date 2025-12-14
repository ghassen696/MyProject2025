from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional
import datetime
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
from collections import defaultdict

router = APIRouter(tags=["Task Verification"])

# -------------------------
# Elasticsearch & Embeddings
# -------------------------
es = Elasticsearch("http://193.95.30.190:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
INDEX_NAME = "employee_classifications"

# -------------------------
# Helper Functions
# -------------------------


def embed_task(task_description: str) -> list:
    """Generate embedding for Elasticsearch query"""
    task_description = task_description.strip()
    if not task_description:
        task_description = "dummy task"
    
    # Encode with normalization
    vec = embedding_model.encode(
        task_description,
        convert_to_numpy=True,
        normalize_embeddings=True  # ✅ Built-in normalization
    )
    
    return vec.tolist()  # ✅ Convert to list for Elasticsearch JSON

def calculate_dynamic_top_k(start_date: str, end_date: str) -> int:
    """
    Calculate appropriate top_k based on date range.
    
    Rule of thumb:
    - 1 day: 50 chunks (enough for 5-10 employees)
    - 7 days: 200 chunks
    - 30 days: 500 chunks
    - 90+ days: 1000 chunks
    """
    start = datetime.date.fromisoformat(start_date)
    end = datetime.date.fromisoformat(end_date)
    days = (end - start).days + 1
    
    if days <= 1:
        return 50
    elif days <= 7:
        return 200
    elif days <= 30:
        return 500
    else:
        return 1000

def search_chunks(task_embedding: list, top_k: int, start_date=None, end_date=None, 
                  employee_id=None) -> List[Dict]:
    """
    Retrieve top matching chunks for the task, optionally filtered by date and employee.
    Returns all matching chunks, to be aggregated per employee later.
    """
    filters = []

    # Date filter
    if start_date and end_date:
        filters.append({"range": {"start_time": {"gte": start_date, "lte": end_date}}})

    # Employee filter
    if employee_id:
        filters.append({"term": {"employee_id": employee_id}})

    bool_query = {"bool": {"must": [{"match_all": {}}]}} if not filters else {"bool": {"filter": filters}}

    # In task_verification.py
    query = {
        "script_score": {
            "query": bool_query,
            "script": {
                "source": """
                    double summary_match = cosineSimilarity(params.query_vector, 'summary_vector');              
                    return summary_match + 1.0;
                """,
                "params": {
                    "query_vector": task_embedding, 
                }
            }
        }
    }

    res = es.search(
        index=INDEX_NAME,
        query=query,   # <-- only the query object here
        size=top_k     # <-- top-level size
    )

    print("Hits found:", len(res["hits"]["hits"]))

    chunks = []
    for hit in res['hits']['hits']:
        src = hit['_source']
        raw_cosine = hit['_score'] - 1.0        # original [-1,1]
        chunks.append({
            "chunk_id": src.get('chunk_id'),
            "employee_id": src.get('employee_id'),
            "category": src.get('category'),
            "confidence": src.get('confidence'),
            "rationale": src.get('rationale'),
            "similarity": raw_cosine,
            "summary_text": src.get('summary_text', ""),
            "start_time": src.get('start_time'),
            "end_time": src.get('end_time')
        })
    return chunks


def calculate_task_coverage(chunks: List[Dict], threshold: float = 0.3) -> Dict:
    """Calculate how well the task was covered by employee's work"""
    if not chunks:
        return {
            "coverage_score": 0.0,
            "evidence_strength": "none",
            "high_match_count": 0,
            "total_chunks": 0
        }
    
    high_matches = [c for c in chunks if c["similarity"] >= threshold]
    avg_similarity = sum(c["similarity"] for c in chunks) / len(chunks)

    # Determine evidence strength
    if avg_similarity >= 0.5 and len(high_matches) >= 3:
        strength = "strong"
    elif avg_similarity >= 0.3 and len(high_matches) >= 2:
        strength = "moderate"
    elif avg_similarity >= 0.1:
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
# Request Schemas
# -------------------------
class TaskQuery(BaseModel):
    task_description: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    top_chunks_per_employee: int = 5
    similarity_threshold: float = 0.0  # Filter low-quality matches

class TaskVerificationQuery(BaseModel):
    """For verifying if specific employees worked on specific tasks"""
    task_description: str
    employee_ids: List[str]  # List of employees to check
    start_date: Optional[str] = None
    end_date: Optional[str] = None

# -------------------------
# API Endpoints
# -------------------------
@router.post("/search")
async def search_tasks(request: TaskQuery):
    """Search for employees who worked on similar tasks in a date range."""
    today = datetime.date.today()
    # Handle dates
    try:
        start_date = request.start_date or (today - datetime.timedelta(days=7)).isoformat()
        end_date = request.end_date or today.isoformat()
    except:
        start_date = (today - datetime.timedelta(days=7)).isoformat()
        end_date = today.isoformat()

    # Generate embedding
    task_embedding = embed_task(request.task_description)

    # Get matching chunks
    dynamic_top_k = calculate_dynamic_top_k(start_date, end_date)
    chunks = search_chunks(task_embedding, start_date=start_date, end_date=end_date,top_k=dynamic_top_k)

    # Aggregate by employee
    employee_dict = defaultdict(list)
    for chunk in chunks:
        if chunk['similarity'] >= request.similarity_threshold:
            employee_dict[chunk['employee_id']].append(chunk)

    employee_results = []
    start_dt = datetime.date.fromisoformat(start_date)
    end_dt = datetime.date.fromisoformat(end_date)
    mid_date = start_dt + (end_dt - start_dt) // 2

    for emp_id, emp_chunks in employee_dict.items():
        emp_chunks_sorted = sorted(emp_chunks, key=lambda x: x['similarity'], reverse=True)
        top_chunks = emp_chunks_sorted[:request.top_chunks_per_employee]

        coverage = calculate_task_coverage(emp_chunks_sorted)

        employee_results.append({
            "employee_id": emp_id,
            "avg_similarity": coverage["coverage_score"],
            "coverage": coverage,
            "top_chunks": [
                {
                    "chunk_id": c["chunk_id"],
                    "similarity": round(c["similarity"], 3),
                    "rationale": c["rationale"],
                    "category": c["category"],
                    "timestamp": c.get("start_time"),
                    "summary": c["summary_text"][:150] + "..." if len(c["summary_text"]) > 150 else c["summary_text"]
                }
                for c in top_chunks
            ]
        })

    employee_results = sorted(employee_results, key=lambda x: x['avg_similarity'], reverse=True)

    return {
        "task": request.task_description,
        "date_range": {"start": start_date, "end": end_date},
        "total_employees_found": len(employee_results),
        "employee_matches": employee_results
    }

@router.get("/")
async def root():
    return {"message": "Task Verification API is running"}
