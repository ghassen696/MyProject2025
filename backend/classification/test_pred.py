import numpy as np
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from sentence_transformers import SentenceTransformer
import math

# -------------------------------
# Configuration
# -------------------------------
ES = Elasticsearch("http://193.95.30.190:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

HISTORY_INDEX = "employee_history"
FEEDBACK_INDEX = "task_feedback"

# Feedback scale
FEEDBACK_SCALE = {
    "strong_decline": -0.15,
    "decline": -0.05,
    "neutral": 0.0,
    "agree": 0.05,
    "strong_agree": 0.15
}

# Decay rate for old feedback (per day)
DECAY_LAMBDA = 0.05

# Embedding update weight for strong_agree
EMBED_UPDATE_WEIGHT = 0.05

# -------------------------------
# Ensure feedback index exists
# -------------------------------
def ensure_feedback_index():
    if ES.indices.exists(FEEDBACK_INDEX):
        return
    mapping = {
        "mappings": {
            "properties": {
                "task_description": {"type": "text"},
                "employee_id": {"type": "keyword"},
                "category": {"type": "keyword"},
                "similarity": {"type": "float"},
                "date": {"type": "date"},
                "feedback": {"type": "keyword"},  # e.g., strong_agree
                "admin_notes": {"type": "text"},
                "created_at": {"type": "date"}
            }
        }
    }
    ES.indices.create(index=FEEDBACK_INDEX, body=mapping)
    print(f"✅ Created index: {FEEDBACK_INDEX}")

# -------------------------------
# Embedding helpers
# -------------------------------
def embed_text(text: str) -> np.ndarray:
    if not text.strip():
        return np.zeros(768)
    return embedding_model.encode(text)

# -------------------------------
# Load employee history
# -------------------------------
def load_employee_history():
    res = ES.search(index=HISTORY_INDEX, size=10000)
    employees = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        if "embedding" in src:
            employees.append({
                "employee_id": src["employee_id"],
                "embedding": np.array(src["embedding"]),
                "dominant_category": src.get("dominant_category", None),
                "summary_text": src.get("summary_text", "")
            })
    return employees

# -------------------------------
# Save feedback
# -------------------------------
def save_feedback(task_description, employee_id, category, similarity, feedback, admin_notes=""):
    doc = {
        "task_description": task_description,
        "employee_id": employee_id,
        "category": category,
        "similarity": similarity,
        "date": datetime.utcnow().date().isoformat(),
        "feedback": feedback,
        "admin_notes": admin_notes,
        "created_at": datetime.utcnow().isoformat()
    }
    ES.index(index=FEEDBACK_INDEX, document=doc)
    print(f"✅ Feedback saved for {employee_id} on task '{task_description}'")

# -------------------------------
# Cosine similarity
# -------------------------------
def cosine_similarity(vec1, vec2):
    if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
        return 0.0
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

# -------------------------------
# Adjust similarity using feedback
# -------------------------------
def adjust_similarity(emp_id, task_category, base_sim):
    # Fetch all feedback for employee and category
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

    # Weighted average with time decay
    weighted_sum = 0
    total_weight = 0
    for doc in feedback_docs:
        fb = doc["_source"]["feedback"]
        fb_score = FEEDBACK_SCALE.get(fb, 0)
        fb_date = datetime.fromisoformat(doc["_source"]["date"])
        days_ago = (datetime.utcnow() - fb_date).days
        decay = math.exp(-DECAY_LAMBDA * days_ago)
        weighted_sum += fb_score * decay
        total_weight += decay
    boost = weighted_sum / total_weight if total_weight > 0 else 0

    # Clamp similarity to [0,1]
    adjusted = min(max(base_sim + boost, 0), 1)
    return adjusted

# -------------------------------
# Optionally update employee embedding
# -------------------------------
def update_employee_embedding(emp, task_vec, feedback):
    if feedback == "strong_agree":
        emp["embedding"] = (1 - EMBED_UPDATE_WEIGHT) * emp["embedding"] + EMBED_UPDATE_WEIGHT * task_vec
        # update in Elasticsearch
        ES.update(index=HISTORY_INDEX, id=emp["employee_id"], doc={"embedding": emp["embedding"].tolist()})

# -------------------------------
# Predict employees for tasks
# -------------------------------
def predict_employees(tasks):
    employees = load_employee_history()
    ensure_feedback_index()

    for task in tasks:
        print(f"\nTask: {task}")
        task_vec = embed_text(task)
        # Assume task category is the first word for simplicity or use a proper NLP classifier
        task_category = task.split()[0]

        similarities = []
        for emp in employees:
            sim = cosine_similarity(task_vec, emp["embedding"])
            sim = adjust_similarity(emp["employee_id"], task_category, sim)
            similarities.append((emp["employee_id"], sim, emp))

        # Sort descending by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Show all candidates
        for i, (emp_id, sim, _) in enumerate(similarities):
            print(f"{i+1}. {emp_id}: similarity {sim:.4f}")

        # Admin feedback
        print("\nProvide feedback using scale: strong_decline, decline, neutral, agree, strong_agree")
        for i, (emp_id, sim, emp) in enumerate(similarities):
            fb = input(f"Feedback for {emp_id}: ").strip().lower()
            if fb not in FEEDBACK_SCALE:
                fb = "neutral"
            save_feedback(task, emp_id, task_category, sim, fb)
            update_employee_embedding(emp, task_vec, fb)

# -------------------------------
# Example usage
# -------------------------------
if __name__ == "__main__":
    tasks_to_assign = [
        "Python Develop backend API",
        "Python Write unit tests for module",
        "Automation Create automation scripts",
    ]
    predict_employees(tasks_to_assign)
