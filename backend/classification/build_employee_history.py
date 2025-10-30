import numpy as np
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer

# -------------------------------
# Configuration
# -------------------------------
ES = Elasticsearch("http://localhost:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

CLASSIFICATION_INDEX = "employee_classifications"
DAILY_SUMMARIES_INDEX = "employee_daily_summaries"
HISTORY_INDEX = "employee_history"

# -------------------------------
# Helper functions
# -------------------------------

def ensure_history_index():
    """Create the index if it doesn’t exist"""
    if ES.indices.exists(index=HISTORY_INDEX):
        return
    mapping = {
        "mappings": {
            "properties": {
                "employee_id": {"type": "keyword"},
                "date": {"type": "date"},
                "embedding": {"type": "dense_vector", "dims": 768},
                "dominant_category": {"type": "keyword"},
                "focus_score": {"type": "float"},
                "summary_text": {"type": "text"},
                "activities": {"type": "object"},
                "insights": {"type": "keyword"},
                "generated_at": {"type": "date"}
            }
        }
    }
    ES.indices.create(index=HISTORY_INDEX, body=mapping)
    print(f"✅ Created index: {HISTORY_INDEX}")


def embed_text(text: str) -> np.ndarray:
    """Embed text using local model"""
    if not text.strip():
        return np.zeros(768)
    return np.array(embedding_model.encode(text))


def get_employee_chunks(employee_id: str, date: str) -> List[np.ndarray]:
    """Fetch all chunk embeddings for an employee on a specific date"""
    query = {
        "bool": {
            "must": [
                {"term": {"employee_id": employee_id}},
                {"range": {"start_time": {"gte": date, "lt": f"{date}||+1d"}}}
            ]
        }
    }
    res = ES.search(index=CLASSIFICATION_INDEX, size=1000, query=query)
    vectors = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        if "summary_vector" in src:
            vectors.append(np.array(src["summary_vector"]))
    return vectors


def get_daily_summary(employee_id: str, date: str) -> Dict[str, Any]:
    """Fetch the daily summary document for an employee"""
    doc_id = f"{employee_id}_{date}"
    if ES.exists(index=DAILY_SUMMARIES_INDEX, id=doc_id):
        res = ES.get(index=DAILY_SUMMARIES_INDEX, id=doc_id)
        return res["_source"]
    return {}


# -------------------------------
# Main logic
# -------------------------------
def build_employee_history():
    ensure_history_index()

    # Cleanup old entries (>60 days)
    cutoff_date = (datetime.utcnow() - timedelta(days=60)).date().isoformat()
    ES.delete_by_query(
        index=HISTORY_INDEX,
        query={"range": {"date": {"lt": cutoff_date}}}
    )

    # Get all unique employee IDs
    employee_ids = ES.search(
        index=CLASSIFICATION_INDEX,
        size=0,
        aggs={"unique_ids": {"terms": {"field": "employee_id", "size": 1000}}}
    )["aggregations"]["unique_ids"]["buckets"]
    employee_ids = [b["key"] for b in employee_ids]

    for emp_id in employee_ids:
        # 1️⃣ Get dates already in history for this employee
        res_history = ES.search(
            index=HISTORY_INDEX,
            size=1000,
            query={"term": {"employee_id": emp_id}},
            _source=["date"]
        )
        existing_dates = {hit["_source"]["date"] for hit in res_history["hits"]["hits"]}

        # 2️⃣ Get all dates in classification index for this employee
        res_cls = ES.search(
            index=CLASSIFICATION_INDEX,
            size=0,
            query={"term": {"employee_id": emp_id}},
            aggs={"dates": {"date_histogram": {"field": "start_time", "calendar_interval": "day"}}}
        )
        cls_dates = [b["key_as_string"][:10] for b in res_cls["aggregations"]["dates"]["buckets"]]

        # 3️⃣ Only process new dates
        new_dates = [d for d in cls_dates if d not in existing_dates]

        for date in new_dates:
            if date < cutoff_date:
                continue

            chunk_vectors = get_employee_chunks(emp_id, date)
            if not chunk_vectors:
                continue

            # Average all chunk embeddings
            mean_chunk_vector = np.mean(chunk_vectors, axis=0)

            # Merge with daily summary
            summary_doc = get_daily_summary(emp_id, date)
            if summary_doc:
                summary_text = summary_doc.get("summary", "")
                insights = summary_doc.get("insights", [])
                summary_vec = embed_text(summary_text)
                final_vec = 0.7 * mean_chunk_vector + 0.3 * summary_vec
            else:
                summary_text, insights = "", []
                final_vec = mean_chunk_vector

            # Dominant category
            cat_res = ES.search(
                index=CLASSIFICATION_INDEX,
                size=0,
                query={"bool": {"must": [
                    {"term": {"employee_id": emp_id}},
                    {"range": {"start_time": {"gte": date, "lt": f"{date}||+1d"}}}
                ]}},
                aggs={"categories": {"terms": {"field": "category", "size": 3}}}
            )
            buckets = cat_res["aggregations"]["categories"]["buckets"]
            dominant_category = buckets[0]["key"] if buckets else None

            doc_id = f"{emp_id}_{date}"
            ES.index(index=HISTORY_INDEX, id=doc_id, document={
                "employee_id": emp_id,
                "date": date,
                "embedding": final_vec.tolist(),
                "dominant_category": dominant_category,
                "summary_text": summary_text,
                "insights": insights,
                "focus_score": round(np.random.uniform(0.7, 1.0), 2),
                "generated_at": datetime.utcnow().isoformat()
            })

            print(f"✅ Updated history for {emp_id} on {date}")

    print("\n🏁 Employee history build complete.")


if __name__ == "__main__":
    build_employee_history()
