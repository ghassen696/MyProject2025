from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import numpy as np
import math

# -------------------------------
# Configuration
# -------------------------------
ES = Elasticsearch("http://localhost:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

HISTORY_INDEX = "employee_history"
FEEDBACK_INDEX = "task_feedback"

FEEDBACK_SCALE = {
    "strong_decline": -0.15,
    "decline": -0.05,
    "neutral": 0.0,
    "agree": 0.05,
    "strong_agree": 0.15
}

DECAY_LAMBDA = 0.05
EMBED_UPDATE_WEIGHT = 0.05

# -------------------------------
# FastAPI setup
# -------------------------------
router = APIRouter(tags=["Employee Task Matcher API"])

# -------------------------------
# Schemas
# -------------------------------

class TaskInput(BaseModel):
    description: str
    category: Optional[str] = None

class TaskListInput(BaseModel):
    tasks: List[TaskInput]

class FeedbackInput(BaseModel):
    task_description: str
    employee_id: str
    category: str
    similarity: float
    feedback: str
    admin_notes: Optional[str] = None

# -------------------------------
# Helper functions
# -------------------------------
def ensure_feedback_index():
    if ES.indices.exists(index=FEEDBACK_INDEX):
        return
    mapping = {
        "mappings": {
            "properties": {
                "task_description": {"type": "text"},
                "employee_id": {"type": "keyword"},
                "category": {"type": "keyword"},
                "similarity": {"type": "float"},
                "date": {"type": "date"},
                "feedback": {"type": "keyword"},
                "admin_notes": {"type": "text"},
                "created_at": {"type": "date"}
            }
        }
    }
    ES.indices.create(index=FEEDBACK_INDEX, body=mapping)

def embed_text(text: str) -> np.ndarray:
    if not text.strip():
        return np.zeros(768)
    return embedding_model.encode(text)

def load_employee_history():
    res = ES.search(index=HISTORY_INDEX, size=10000)
    employees = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        if "embedding" in src:
            employees.append({
                "employee_id": src["employee_id"],
                "embedding": np.array(src["embedding"]),
                "dominant_category": src.get("dominant_category"),
                "summary_text": src.get("summary_text", "")
            })
    return employees

def cosine_similarity(vec1, vec2):
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def adjust_similarity(emp_id, task_category, base_sim):
    res = ES.search(
        index=FEEDBACK_INDEX,
        size=1000,
        query={"bool": {"must": [
            {"term": {"employee_id": emp_id}},
            {"term": {"category": task_category}}
        ]}}
    )
    feedback_docs = res["hits"]["hits"]
    if not feedback_docs:
        return base_sim

    weighted_sum, total_weight = 0, 0
    for doc in feedback_docs:
        fb = doc["_source"]["feedback"]
        fb_score = FEEDBACK_SCALE.get(fb, 0)
        fb_date = datetime.fromisoformat(doc["_source"]["date"])
        days_ago = (datetime.utcnow() - fb_date).days
        decay = math.exp(-DECAY_LAMBDA * days_ago)
        weighted_sum += fb_score * decay
        total_weight += decay

    boost = weighted_sum / total_weight if total_weight > 0 else 0
    return min(max(base_sim + boost, 0), 1)

def update_employee_embedding(emp, task_vec, feedback):
    if feedback == "strong_agree":
        emp["embedding"] = (1 - EMBED_UPDATE_WEIGHT) * emp["embedding"] + EMBED_UPDATE_WEIGHT * task_vec
        ES.update(index=HISTORY_INDEX, id=emp["employee_id"], doc={"embedding": emp["embedding"].tolist()})

# -------------------------------
# API Endpoints
# -------------------------------

@router.post("/predict")
def predict_employees_bulk(task_list: TaskListInput):
    ensure_feedback_index()
    employees = load_employee_history()
    results_list = []

    for task in task_list.tasks:
        task_vec = embed_text(task.description)
        task_category = task.category or task.description.split()[0]

        results = []
        for emp in employees:
            base_sim = cosine_similarity(task_vec, emp["embedding"])
            adjusted = adjust_similarity(emp["employee_id"], task_category, base_sim)
            results.append({
                "employee_id": emp["employee_id"],
                "similarity": round(adjusted, 4)
            })

        results.sort(key=lambda x: x["similarity"], reverse=True)
        results_list.append({
            "task": task.description,
            "category": task_category,
            "recommendations": results
        })

    return results_list

@router.post("/feedback")
def submit_feedback(feedback: FeedbackInput):
    """
    Store admin feedback and optionally update embeddings.
    """
    doc = {
        "task_description": feedback.task_description,
        "employee_id": feedback.employee_id,
        "category": feedback.category,
        "similarity": feedback.similarity,
        "date": datetime.utcnow().date().isoformat(),
        "feedback": feedback.feedback,
        "admin_notes": feedback.admin_notes,
        "created_at": datetime.utcnow().isoformat()
    }
    ES.index(index=FEEDBACK_INDEX, document=doc)

    # Update embedding if feedback is strong_agree
    if feedback.feedback == "strong_agree":
        task_vec = embed_text(feedback.task_description)
        emp_hit = ES.search(index=HISTORY_INDEX, query={"term": {"employee_id": feedback.employee_id}})
        if emp_hit["hits"]["hits"]:
            emp_doc = emp_hit["hits"]["hits"][0]["_source"]
            emp_vec = np.array(emp_doc["embedding"])
            new_vec = (1 - EMBED_UPDATE_WEIGHT) * emp_vec + EMBED_UPDATE_WEIGHT * task_vec
            ES.update(index=HISTORY_INDEX, id=emp_hit["hits"]["hits"][0]["_id"], doc={"embedding": new_vec.tolist()})

    return {"status": "success", "message": f"Feedback saved for {feedback.employee_id}"}


class BulkFeedbackInput(BaseModel):
    feedbacks: List[FeedbackInput]

@router.post("/feedback/bulk")
def submit_bulk_feedback(feedback_data: BulkFeedbackInput):
    for fb in feedback_data.feedbacks:
        submit_feedback(fb)
    return {"status": "success", "message": f"{len(feedback_data.feedbacks)} feedbacks saved"}
