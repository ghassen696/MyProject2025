import re
import numpy as np
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from typing import Dict, Any, List
from sentence_transformers import SentenceTransformer
from collections import defaultdict

# -------------------------------
# Configuration
# -------------------------------
ES = Elasticsearch("http://193.95.30.190:9200")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

CLASSIFICATION_INDEX = "employee_classifications"
DAILY_SUMMARIES_INDEX = "employee_daily_summaries"
HISTORY_INDEX = "employee_history"
KPI_INDEX = "employee_kpi_summary4"

# =====================================
# SKILL EXTRACTION FROM WINDOWS
# =====================================

# Comprehensive skill mapping
SKILL_PATTERNS = {
    # Programming Languages
    r'\.py\b|python': ['Python'],
    r'\.js\b|javascript|node': ['JavaScript', 'Node.js'],
    r'\.ts\b|typescript': ['TypeScript'],
    r'\.java\b': ['Java'],
    r'\.cpp\b|\.c\b': ['C/C++'],
    r'\.go\b': ['Go'],
    r'\.rs\b|rust': ['Rust'],
    
    # Frameworks & Libraries
    r'fastapi|router\.py': ['FastAPI', 'Backend Development'],
    r'django': ['Django', 'Backend Development'],
    r'flask': ['Flask', 'Backend Development'],
    r'react|\.tsx\b|\.jsx\b': ['React', 'Frontend Development'],
    r'vue': ['Vue.js', 'Frontend Development'],
    r'angular': ['Angular', 'Frontend Development'],
    
    # Data & AI/ML
    r'pandas|numpy|jupyter': ['Data Analysis', 'Python'],
    r'tensorflow|keras|pytorch': ['Machine Learning', 'Deep Learning'],
    r'sklearn|scikit': ['Machine Learning'],
    r'pipeline': ['Data Pipelines', 'ETL'],
    
    # Databases & Search
    r'elasticsearch|elastic': ['Elasticsearch', 'Search Engineering'],
    r'postgres|postgresql': ['PostgreSQL', 'Database'],
    r'mysql': ['MySQL', 'Database'],
    r'mongodb': ['MongoDB', 'NoSQL'],
    r'redis': ['Redis', 'Caching'],
    
    # DevOps & Tools
    r'docker|dockerfile': ['Docker', 'Containerization'],
    r'kubernetes|k8s': ['Kubernetes', 'Orchestration'],
    r'terraform': ['Terraform', 'IaC'],
    r'jenkins|github actions': ['CI/CD'],
    
    # Development Tools
    r'visual studio code|vscode|code\.exe': ['VS Code', 'Development'],
    r'cursor': ['AI-Assisted Development', 'Development'],
    r'git': ['Git', 'Version Control'],
    
    # Design & Documentation
    r'lucidchart': ['Diagramming', 'System Design'],
    r'figma': ['UI/UX Design'],
    r'\.md\b|markdown': ['Documentation'],
    r'\.tex\b|latex': ['LaTeX', 'Technical Writing'],
    
    # Web & APIs
    r'chrome|edge|browser': ['Web Research'],
    r'api|rest|graphql': ['API Development'],
    r'localhost:\d+': ['Local Development', 'Testing'],
    
    # Business Tools
    r'google (docs|sheets|slides)': ['Google Workspace'],
    r'excel|spreadsheet': ['Data Analysis', 'Excel'],
    r'powerpoint|presentation': ['Presentations'],
    
    # AI Tools
    r'claude|chatgpt|gemini': ['AI Tools', 'Prompt Engineering'],
    r'copilot': ['AI-Assisted Development'],
    
    # Specific Tasks
    r'classification|prediction': ['Machine Learning', 'Classification'],
    r'embedding|vector': ['Vector Search', 'Embeddings'],
    r'kpi|analytics|dashboard': ['Analytics', 'Data Visualization'],
    r'report|summary': ['Reporting', 'Analysis'],
    r'router|endpoint': ['Backend Development', 'API Development'],
}


# -------------------------------
# Helper functions
# -------------------------------

def ensure_history_index():
    """Create the index if it doesn't exist"""
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
                "skills": {"type": "object"},  # Changed to object for scores
                "activity_distribution": {"type": "object"},
                "peak_hours": {"type": "integer"},
                "primary_tools": {"type": "keyword"},  # NEW
                "generated_at": {"type": "date"}
            }
        }
    }
    ES.indices.create(index=HISTORY_INDEX, body=mapping)
    print(f"✅ Created index: {HISTORY_INDEX}")

def normalize_vector(vec: np.ndarray) -> np.ndarray:
    """Normalize a vector to unit length"""
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm

def get_employee_chunks(employee_id: str, date: str) -> List[np.ndarray]:
    """Fetch all chunk embeddings for an employee on a specific date"""
    query = {
        "bool": {
            "must": [
                {"term": {"employee_id": employee_id}},
                {"range": {"start_time": {"gte": date, "lt": f"{date}||+1d"}}}
            ],
            "filter": [
                {"range": {"confidence": {"gte": 0.5}}}
            ]
        }
    }
    res = ES.search(index=CLASSIFICATION_INDEX, size=1000, query=query)
    vectors = []
    for hit in res["hits"]["hits"]:
        src = hit["_source"]
        if "summary_vector" in src and "rationale_vector" in src:
            summary_vec = np.array(src["summary_vector"])
            rationale_vec = np.array(src["rationale_vector"])
            combined = 0.6 * summary_vec + 0.4 * rationale_vec
            combined = normalize_vector(combined)
            vectors.append(combined)
    return vectors

def get_daily_summary(employee_id: str, date: str) -> Dict[str, Any]:
    """Fetch the daily summary document for an employee"""
    doc_id = f"{employee_id}_{date}"
    if ES.exists(index=DAILY_SUMMARIES_INDEX, id=doc_id):
        res = ES.get(index=DAILY_SUMMARIES_INDEX, id=doc_id)
        return res["_source"]
    return {}

def get_productivity_score(employee_id: str, date: str) -> float:
    """Fetch productivity_score and normalize to 0-1 range"""
    doc_id = f"{employee_id}-{date}"
    
    try:
        kpi_doc = ES.get(index=KPI_INDEX, id=doc_id)
        score = kpi_doc["_source"].get("productivity_score", 50.0)
        return round(score / 100, 3)
    except Exception as e:
        print(f"⚠️ Could not fetch productivity score for {employee_id} on {date}: {e}")
        return 0.5

def extract_skills_from_windows(employee_id: str, date: str) -> Dict[str, float]:
    """
    Extract skills with confidence scores from window titles + time spent
    
    Returns:
        {"Python": 0.85, "FastAPI": 0.65, "Elasticsearch": 0.50, ...}
    """
    doc_id = f"{employee_id}-{date}"
    
    try:
        kpi_doc = ES.get(index=KPI_INDEX, id=doc_id)
        time_per_window = kpi_doc["_source"].get("time_per_window", [])
        top_windows = kpi_doc["_source"].get("top_windows", [])
        
    except Exception as e:
        print(f"⚠️ Could not fetch windows for {employee_id} on {date}: {e}")
        return {}
    
    skill_scores = defaultdict(float)
    total_time = 0
    
    for window_entry in time_per_window:
        window = window_entry.get("window", "").lower()
        time_spent = window_entry.get("time_spent_min", 0)
        
        if time_spent < 2:
            continue
        
        total_time += time_spent
        
        for pattern, skills in SKILL_PATTERNS.items():
            if re.search(pattern, window, re.IGNORECASE):
                for skill in skills:
                    time_weight = min(1.5, 0.5 + (time_spent / 20))
                    skill_scores[skill] += time_weight
    
    # Factor in switch count
    for window_entry in top_windows:
        window = window_entry.get("window", "").lower()
        switch_count = window_entry.get("switch_count", 0)
        
        if switch_count > 20:
            for pattern, skills in SKILL_PATTERNS.items():
                if re.search(pattern, window, re.IGNORECASE):
                    for skill in skills:
                        skill_scores[skill] += 0.3
    
    if not skill_scores:
        return {}
    
    max_score = max(skill_scores.values())
    normalized_skills = {
        skill: round(min(score / max_score, 1.0), 3)
        for skill, score in skill_scores.items()
    }
    
    sorted_skills = sorted(normalized_skills.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_skills[:15])

def get_primary_tools(employee_id: str, date: str) -> List[str]:
    """
    Get top 5 tools/applications by time spent
    
    Returns:
        ["VS Code", "Chrome", "Elasticsearch", "Claude AI", "Lucidchart"]
    """
    doc_id = f"{employee_id}-{date}"
    
    try:
        kpi_doc = ES.get(index=KPI_INDEX, id=doc_id)
        time_per_window = kpi_doc["_source"].get("time_per_window", [])
        
    except Exception as e:
        return []
    
    tool_time = defaultdict(float)
    
    for window_entry in time_per_window:
        window = window_entry.get("window", "").lower()
        time_spent = window_entry.get("time_spent_min", 0)
        
        if "visual studio code" in window or "code.exe" in window:
            tool_time["VS Code"] += time_spent
        elif "chrome" in window:
            tool_time["Chrome"] += time_spent
        elif "claude" in window:
            tool_time["Claude AI"] += time_spent
        elif "lucidchart" in window:
            tool_time["Lucidchart"] += time_spent
        elif "elasticsearch" in window or "kibana" in window:
            tool_time["Elasticsearch"] += time_spent
        elif "chatgpt" in window:
            tool_time["ChatGPT"] += time_spent
        elif "google docs" in window or "google sheets" in window:
            tool_time["Google Workspace"] += time_spent
        elif "slack" in window or "teams" in window:
            tool_time["Communication Tools"] += time_spent
    
    sorted_tools = sorted(tool_time.items(), key=lambda x: x[1], reverse=True)
    return [tool for tool, _ in sorted_tools[:5]]



def get_peak_hours(employee_id: str, date: str) -> List[int]:
    """Identify employee's most productive hours"""
    doc_id = f"{employee_id}-{date}"
    
    try:
        kpi_doc = ES.get(index=KPI_INDEX, id=doc_id)
        typing_data = kpi_doc["_source"].get("typing_per_hour", [])
        
        sorted_hours = sorted(typing_data, 
                            key=lambda x: x["chars_per_hour"], 
                            reverse=True)
        
        return [h["hour"] for h in sorted_hours[:3]]
    except Exception as e:
        print(f"⚠️ Could not fetch peak hours for {employee_id} on {date}: {e}")
        return []

# -------------------------------
# Main logic
# -------------------------------
def build_employee_history():
    ensure_history_index()

    cutoff_date = (datetime.utcnow() - timedelta(days=60)).date().isoformat()
    ES.delete_by_query(
        index=HISTORY_INDEX,
        query={"range": {"date": {"lt": cutoff_date}}}
    )

    employee_ids = ES.search(
        index=CLASSIFICATION_INDEX,
        size=0,
        aggs={"unique_ids": {"terms": {"field": "employee_id", "size": 1000}}}
    )["aggregations"]["unique_ids"]["buckets"]
    employee_ids = [b["key"] for b in employee_ids]

    for emp_id in employee_ids:
        res_history = ES.search(
            index=HISTORY_INDEX,
            size=1000,
            query={"term": {"employee_id": emp_id}},
            _source=["date"]
        )
        existing_dates = {hit["_source"]["date"] for hit in res_history["hits"]["hits"]}

        res_cls = ES.search(
            index=CLASSIFICATION_INDEX,
            size=0,
            query={"term": {"employee_id": emp_id}},
            aggs={"dates": {"date_histogram": {"field": "start_time", "calendar_interval": "day"}}}
        )
        cls_dates = [b["key_as_string"][:10] for b in res_cls["aggregations"]["dates"]["buckets"]]

        new_dates = [d for d in cls_dates if d not in existing_dates]

        for date in new_dates:
            if date < cutoff_date:
                continue

            chunk_vectors = get_employee_chunks(emp_id, date)
            if not chunk_vectors:
                continue

            final_vec = np.mean(chunk_vectors, axis=0)
            final_vec = normalize_vector(final_vec)

            summary_doc = get_daily_summary(emp_id, date)
            if summary_doc:
                summary_text = summary_doc.get("summary", "")
                insights = summary_doc.get("insights", [])
            else:
                summary_text, insights = "", []

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
            
            # ✅ UPDATED: Now using enhanced skill extraction
            ES.index(index=HISTORY_INDEX, id=doc_id, document={
                "employee_id": emp_id,
                "date": date,
                "embedding": final_vec.tolist(),
                "dominant_category": dominant_category,
                "summary_text": summary_text,
                "insights": insights,
                "productivity_score": get_productivity_score(emp_id, date),
                "skills": extract_skills_from_windows(emp_id, date),  # ✅ ENHANCED
                "primary_tools": get_primary_tools(emp_id, date),  # ✅ NEW
                "peak_hours": get_peak_hours(emp_id, date),
                "generated_at": datetime.utcnow().isoformat()
            })

            print(f"✅ Updated history for {emp_id} on {date}")

    print("\n🏁 Employee history build complete.")

if __name__ == "__main__":
    build_employee_history()
    