from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from elasticsearch import Elasticsearch
from app.config import SKILL_PATTERNS
from sentence_transformers import SentenceTransformer
import numpy as np
import math
import time
import re
from collections import defaultdict

# -------------------------------
# Configuration
# -------------------------------
ES = Elasticsearch("http://193.95.30.190:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

HISTORY_INDEX = "employee_history"
FEEDBACK_INDEX = "task_feedback"
FEEDBACK_SIMILARITY_THRESHOLD = 0.4  
FEEDBACK_SCALE = {
    "strong_decline": -0.15,
    "decline": -0.05,
    "neutral": 0.0,
    "agree": 0.05,
    "strong_agree": 0.15
}
FEEDBACK_WEIGHT_MULTIPLIER = {
    "strong_decline": 2.0, 
    "decline": 1.0,
    "neutral": 1.0,
    "agree": 1.0,
    "strong_agree": 2.0  
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

class TaskListInput(BaseModel):
    tasks: List[TaskInput]

class FeedbackInput(BaseModel):
    task_description: str
    employee_id: str
    category: str
    similarity: float
    feedback: str

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
                "created_at": {"type": "date"},
                "task_embedding": {"type": "dense_vector", "dims": 768}
            }
        }
    }
    ES.indices.create(index=FEEDBACK_INDEX, body=mapping)

def embed_text(text: str) -> np.ndarray:
    if not text.strip():
        return np.zeros(768)
    vec = embedding_model.encode(text, normalize_embeddings=True)
    return vec / np.linalg.norm(vec) if np.linalg.norm(vec) > 0 else vec
     

def load_employee_history():
    """Load ALL history documents (all days for all employees)"""
    res = ES.search(index=HISTORY_INDEX, size=10000)
    all_history = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        if "embedding" in src:
            all_history.append({
                "employee_id": src["employee_id"],
                "embedding": np.array(src["embedding"]),
                "dominant_category": src.get("dominant_category"),
                "summary_text": src.get("summary_text", ""),
                "productivity_score": src.get("productivity_score", 0.7),
                "skills": src.get("skills", {}),
                "date": src.get("date", ""),
                "activity_distribution": src.get("activity_distribution", {})
            })
    return all_history

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2)

def adjust_similarity(emp_id, base_sim, task_vec):
    """
    Hybrid feedback adjustment:
    1. Filter by employee_id + category
    2. Check semantic similarity between current task and feedback task
    3. Apply weighted boost only for similar tasks
    """
    res = ES.search(
        index=FEEDBACK_INDEX,
        size=1000,
        query={"term": {"employee_id": emp_id}},
            sort=[{"created_at": {"order": "desc"}}]
    )
    feedback_docs = res["hits"]["hits"]
    if not feedback_docs:
        return {
            "adjusted_score": base_sim,
            "feedback_boost": 0.0,
            "relevant_feedback_count": 0
        }

    weighted_sum, total_weight = 0, 0
    relevant_count = 0
    
    for doc in feedback_docs:
        src = doc["_source"]
        
        # Skip if no embedding stored (legacy feedback)
        if "task_embedding" not in src:
            continue
        
        # Calculate semantic similarity between tasks
        feedback_task_vec = np.array(src["task_embedding"])
        task_similarity = cosine_similarity(task_vec, feedback_task_vec)
        
        # Only apply feedback if tasks are similar enough
        if task_similarity < FEEDBACK_SIMILARITY_THRESHOLD:
            continue
        
        relevant_count += 1
        
        # Get feedback score and time decay
        fb = src["feedback"]
        fb_score = FEEDBACK_SCALE.get(fb, 0)
        fb_date = datetime.fromisoformat(src["date"])
        days_ago = (datetime.utcnow() - fb_date).days
        time_decay = math.exp(-DECAY_LAMBDA * days_ago)
        
        # Get the weight multiplier for this feedback type
        weight_power = FEEDBACK_WEIGHT_MULTIPLIER.get(fb, 1.0)
        
        # Weight by task similarity with multiplier
        similarity_weight = task_similarity ** weight_power
        
        # Combined weight: time_decay * similarity_weight
        combined_weight = time_decay * similarity_weight
        
        weighted_sum += fb_score * combined_weight
        total_weight += combined_weight

    boost = weighted_sum / total_weight if total_weight > 0 else 0
    adjusted_score = min(max(base_sim + boost, 0), 1)
    
    return {
        "adjusted_score": adjusted_score,
        "feedback_boost": round(boost, 4),
        "relevant_feedback_count": relevant_count
    }
"""def update_employee_embedding(emp, task_vec, feedback):
    if feedback == "strong_agree":
        emp["embedding"] = (1 - EMBED_UPDATE_WEIGHT) * emp["embedding"] + EMBED_UPDATE_WEIGHT * task_vec
        ES.update(index=HISTORY_INDEX, id=emp["employee_id"], doc={"embedding": emp["embedding"].tolist()})
"""

def calculate_multi_factor_score(base_sim: float, emp: dict, task_description: str,
                                  current_date: str) -> dict:
    """
    Calculate final score with multiple factors:
    - Semantic match (60%)
    - skills match (15%)
    - productivity score (15%)
    - Recency weight (10%)
    """
    
    # 1. Semantic match (60%)
    semantic_score = base_sim * 0.6
    
# 1. Extract skill keywords from task description
    task_skills = []
    for pattern, skills in SKILL_PATTERNS.items():
        if re.search(pattern, task_description, re.IGNORECASE):
            task_skills.extend(skills)

    # 2. Score employee based on these skills
    skills_score = 0
    for skill in task_skills:
        skills_score = max(skills_score, emp.get("skills", {}).get(skill, 0))
    skills_score *= 0.15

    # 3. Focus score (15%)
    productivity_score = emp.get("productivity_score", 0.5)
    productivity_score = productivity_score * 0.15
    
    # 4. Recency weight (10%)
    emp_date = emp.get("date", current_date)
    try:
        days_old = (datetime.fromisoformat(current_date) - 
                   datetime.fromisoformat(emp_date)).days
        recency_decay = math.exp(-0.02 * days_old)  # Decays over 50 days
    except:
        recency_decay = 1.0
    recency_score = recency_decay * 0.1
    
    final_score = semantic_score + skills_score + productivity_score + recency_score
    
    return {
        "final_score": round(final_score, 4),
        "breakdown": {
            "semantic": round(semantic_score, 4),
            "skills_score": round(skills_score, 4),
            "productivity_score": round(productivity_score, 4),
            "recency": round(recency_score, 4)
        }
    }


def generate_recommendation_rationale(emp: dict,
                                     scoring: dict) -> str:
    """Generate human-readable explanation"""
    
    rationale_parts = []
    
    # Semantic match
    if scoring["breakdown"]["semantic"] > 0.35:
        rationale_parts.append(f"Strong semantic match ({scoring['breakdown']['semantic']:.1%})")
    
    # Category fit
    if scoring["breakdown"]["skills_score"] > 0.05:
        top_skills = list(emp.get("skills", {}).keys())[:3]
        rationale_parts.append(f"Skills match: {', '.join(top_skills)}")

    
    # Focus level
    productivity_score = emp.get("productivity_score", 0.5)
    if productivity_score > 0.6:
        rationale_parts.append(f"High productivity score ({productivity_score:.2f})")
    elif productivity_score < 0.5:
        rationale_parts.append(f"Moderate productivity ({productivity_score:.2f})")
    
    if not rationale_parts:
        rationale_parts.append("General match")
    
    return " | ".join(rationale_parts)


# -------------------------------
# API Endpoints
# -------------------------------

@router.post("/predict")
def predict_employees_bulk(task_list: TaskListInput):
    
    start = time.time()
    ensure_feedback_index()
    all_history = load_employee_history()  # All days for all employees
    current_date = datetime.utcnow().date().isoformat()
    results_list = []

    for task in task_list.tasks:
        task_vec = embed_text(task.description)
        #task_category = task.category or "General"

        # Group history by employee_id and filter by semantic threshold
        employee_days = defaultdict(list)
        
        for history_doc in all_history:
            # STEP 1: Semantic pre-filter (40% threshold)
            base_sim = cosine_similarity(task_vec, history_doc["embedding"])
            
            if base_sim < 0.1:  # Skip irrelevant days
                continue
            # STEP 2: Apply feedback adjustment (now returns dict)
            feedback_result = adjust_similarity(
                history_doc["employee_id"], 
                base_sim,
                task_vec  
            )
            adjusted_sim = feedback_result["adjusted_score"]
            
            # STEP 3: Calculate full multi-factor score for this day
            scoring = calculate_multi_factor_score(
                adjusted_sim, 
                history_doc, 
                task.description, 
                current_date
            )
            # STEP 4: Store this day's score with feedback info
            employee_days[history_doc["employee_id"]].append({
                "score": scoring["final_score"],
                "breakdown": scoring["breakdown"],
                "date": history_doc["date"],
                "skills": history_doc["skills"],
                "productivity_score": history_doc["productivity_score"],
                "dominant_category": history_doc["dominant_category"],
                "summary_text": history_doc["summary_text"],
                "feedback_boost": feedback_result["feedback_boost"],
                "relevant_feedback_count": feedback_result["relevant_feedback_count"]
            })
        
        # STEP 5: Average scores per employee
        results = []
        for emp_id, days in employee_days.items():
            if not days:
                continue
            
            # Simple average of all matching days
            avg_score = sum(d["score"] for d in days) / len(days)
            
            # Get the best day for reference
            best_day = max(days, key=lambda d: d["score"])
            
            # Use most recent day's data for display
            most_recent = max(days, key=lambda d: d["date"])
            results.append({
                "employee_id": emp_id,
                "similarity": round(avg_score, 4),
                "matching_days": len(days),
                "best_day_score": round(best_day["score"], 4),
                "date_range": f"{min(d['date'] for d in days)} to {max(d['date'] for d in days)}",
                "rationale": generate_recommendation_rationale(
                    most_recent, 
                    #task_category, 
                    {"breakdown": most_recent["breakdown"]}
                ),
                "score_breakdown": {
                    "avg_semantic": round(sum(d["breakdown"]["semantic"] for d in days) / len(days), 4),
                    "avg_skills": round(sum(d["breakdown"]["skills_score"] for d in days) / len(days), 4),
                    "avg_productivity": round(sum(d["breakdown"]["productivity_score"] for d in days) / len(days), 4),
                    "avg_recency": round(sum(d["breakdown"]["recency"] for d in days) / len(days), 4)
                },
                "dominant_category": most_recent["dominant_category"],
                "productivity_score": most_recent["productivity_score"],
                "skills": dict(list(most_recent["skills"].items())[:5]),
                # Feedback debug info
                "avg_feedback_boost": round(sum(d["feedback_boost"] for d in days) / len(days), 4),
                "total_relevant_feedback": sum(d["relevant_feedback_count"] for d in days)
            })
        # STEP 6: Sort by average score and return top 10
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        results_list.append({
            "task": task.description,
            #"category": task_category,
            "recommendations": results[:10]
        })
    
    latency = time.time() - start
    print(f"Query latency: {latency:.2f} seconds")
    return results_list



@router.post("/feedback")
def submit_feedback(feedback: FeedbackInput):
    """
    Store admin feedback with task embedding for hybrid matching.
    """
    # Embed the task description for semantic matching
    task_embedding = embed_text(feedback.task_description)
    
    doc = {
        "task_description": feedback.task_description,
        "employee_id": feedback.employee_id,
        "category": feedback.category,
        "similarity": feedback.similarity,
        "date": datetime.utcnow().date().isoformat(),
        "feedback": feedback.feedback,
        "created_at": datetime.utcnow().isoformat(),
        "task_embedding": task_embedding.tolist()  # Store embedding for hybrid matching
    }
    ES.index(index=FEEDBACK_INDEX, document=doc)

    return {"status": "success", "message": f"Feedback saved for {feedback.employee_id}"}

class BulkFeedbackInput(BaseModel):
    feedbacks: List[FeedbackInput]

@router.post("/feedback/bulk")
def submit_bulk_feedback(feedback_data: BulkFeedbackInput):
    for fb in feedback_data.feedbacks:
        submit_feedback(fb)
    return {"status": "success", "message": f"{len(feedback_data.feedbacks)} feedbacks saved"}