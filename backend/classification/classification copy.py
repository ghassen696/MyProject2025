# enhanced_classification.py
from concurrent.futures import ThreadPoolExecutor, as_completed
from elasticsearch import Elasticsearch
from datetime import datetime
import json
import time
import requests
from typing import List, Dict, Any
import numpy as np

# -------------------------
# Configuration
# -------------------------
OLLAMA_MODEL = "llama3.2:latest"
OLLAMA_URL = "http://193.95.30.190:11434"  # replace with your Ollama endpoint
MAX_RETRIES = 3
TEMPERATURE = 0.2
MAX_WORKERS = 6  # Tune this based on CPU/network

# -------------------------
# JSON Parsing Helper
# -------------------------
def parse_json_response(resp_text: str) -> dict:
    """Robustly parse JSON from model response."""
    try:
        return json.loads(resp_text)
    except json.JSONDecodeError:
        start = resp_text.find("{")
        end = resp_text.rfind("}") + 1
        if start != -1 and end != -1:
            try:
                return json.loads(resp_text[start:end])
            except json.JSONDecodeError:
                pass
    return {"category": "Unknown", "confidence": 0.0, "rationale": "Failed to parse JSON"}

# -------------------------
# Classification Helper
# -------------------------
def classify_activity(chunk: Dict[str, Any], retries: int = MAX_RETRIES, temperature: float = TEMPERATURE) -> Dict[str, Any]:
    """Classify a chunk of logs into a semantic activity category using Ollama."""
    
    text = chunk.get("summary_text", "")
    dominant_event = chunk.get("meta", {}).get("dominant_event", "unknown")
    event_count = chunk.get("meta", {}).get("original_event_count", 0)
    window = chunk.get("window", "unknown")
    start_time = chunk.get("start_time", "unknown")
    end_time = chunk.get("end_time", "unknown")

    prompt = f"""
You are an AI assistant specialized in analyzing summarized logs of cloud engineers at Huawei.

Your task is to classify the dominant activity category for the following time window. 
Consider the summary of actions, the dominant window/application, and metadata like event counts and duration.

Metadata:
- Dominant event: {dominant_event}
- Event count: {event_count}
- Window/application: {window}
- Chunk duration: from {start_time} to {end_time}
- Quality score: {chunk.get('meta', {}).get('quality', {}).get('quality_score', 'unknown')}
- Unique apps: {chunk.get('meta', {}).get('quality', {}).get('unique_apps', 0)}
- Meaningful content: {chunk.get('meta', {}).get('quality', {}).get('has_meaningful_content', False)}

Possible categories:
1. Development / Coding - writing code, debugging, code review, scripting (VS Code, IntelliJ, PyCharm)
2. Cloud Operations / DevOps - managing cloud resources, deployments, CI/CD, monitoring (Huawei Cloud console, Jenkins)
3. System Maintenance / Troubleshooting - server maintenance, error resolution, log analysis, production incidents
4. Meetings / Communication - internal calls, emails, chat, planning (WeLink, Teams, Outlook)
5. Research / Learning - reading documentation, tutorials, studying new frameworks or cloud services
6. Administrative / Reporting - timesheets, HR tools, internal dashboards, tickets (JIRA)
7. Browsing / Distraction - non-work web browsing, social media, personal email
8. Idle / Break - away from keyboard, lunch, personal breaks
9. Automation / Scripting - writing scripts, batch jobs, automation tasks

Instructions:
- Base your classification on the **summary_text** and metadata above.
- Consider the dominant window/application as a strong hint.
- Return ONLY valid JSON in this format:
{{"category": str, "confidence": float, "rationale": str}}
- Rationale should be concise (2-3 sentences), explain why this chunk belongs to the category, highlight key actions/tools/context, and capture the semantic activity.
- include the names of projects, files, applications , window,application, url or ports that were actively used if they support understanding the category.
- The rationale should be written so it can be used for embedding and similarity comparisons to task descriptions.
IMPORTANT: Do NOT include any text outside the JSON object.
Chunk Summary:
{text}
"""

    for attempt in range(retries):
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "options": {"temperature": temperature},
                "stream": False,
            }
            resp = requests.post(OLLAMA_URL + "/api/generate", json=payload, timeout=240)
            resp.raise_for_status()
            response_text = resp.json().get("response", "").strip()
            parsed = parse_json_response(response_text)
            if "category" in parsed and "confidence" in parsed:
                # --- Fallback heuristics if category is Unknown or JSON failed ---
                category = parsed.get("category", "Unknown")
                if category.lower() in ["unknown", "none", "error"]:
                    text_lower = text.lower()

                    # --- Refined heuristic classification ---
                    if any(k in text_lower for k in ["stackoverflow", "developer.huawei", "docs.huawei", "tutorial", "documentation", "research", "learn"]):
                        category = "Research / Learning"

                    elif any(k in text_lower for k in ["facebook", "youtube", "instagram", "netflix", "reddit", "twitter", "gmail", "chrome personal", "news", "entertainment"]):
                        category = "Browsing / Distraction"

                    elif any(k in text_lower for k in ["chrome", "google", "wikipedia", "search", "browser"]):
                        category = "Browsing / Research"

                    elif any(k in text_lower for k in ["code", "visual studio", "pycharm", "intellij", "vscode", "sublime", "notepad++", ".py", ".java", ".js"]):
                        category = "Development / Coding"

                    elif any(k in text_lower for k in ["terminal", "bash", "shell", "cmd", "powershell", "ecs-ai", "server", "log", "error", "monitoring"]):
                        category = "System Maintenance / Troubleshooting"

                    elif any(k in text_lower for k in ["welink", "teams", "outlook", "meeting", "call", "chat", "slack", "email"]):
                        category = "Meetings / Communication"

                    elif any(k in text_lower for k in ["jira", "ticket", "report", "dashboard", "timesheet", "form", "hr", "admin"]):
                        category = "Administrative / Reporting"

                    elif any(k in text_lower for k in ["jenkins", "deploy", "pipeline", "cicd", "build", "kubernetes", "docker", "cloud", "serverless"]):
                        category = "Cloud Operations / DevOps"

                    elif any(k in text_lower for k in ["break", "idle", "afk", "lunch", "coffee", "away"]):
                        category = "Idle / Break"

                    else:
                        category = "Context Switching / Unclear"


                    parsed.update({
                        "category": category,
                        "confidence": 0.3,  
                        "rationale": parsed.get("rationale", "") + " | Heuristic fallback applied based on keywords."
                    })

                return parsed
        except Exception as e:
            print(f"[classify_activity] Error: {e}. Retry {attempt+1}/{retries}...")
            time.sleep(2)

    return {"category": "Unknown", "confidence": 0.0, "rationale": "Failed after retries."}
# -------------------------
# Embedding
# -------------------------
# -------------------------
# Embedding Helper
# -------------------------
from sentence_transformers import SentenceTransformer
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
# Load embedding model
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

def embed_text_batch(texts: List[str]) -> list:
    """
    Generate a vector embedding for the given text.
    Returns a Python list of floats (suitable for Elasticsearch).
    """
    if not texts:
        return []
    return embedding_model.encode(texts, convert_to_numpy=True).tolist()

# -------------------------
# Batch Classification
# -------------------------

def batch_classify_parallel(chunks: List[Dict[str, Any]], max_workers: int = MAX_WORKERS) -> List[Dict[str, Any]]:
    """Run classification for many chunks in parallel and attach results to each chunk."""
    enriched_chunks = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {executor.submit(classify_activity, chunk): chunk for chunk in chunks}
        for i, future in enumerate(as_completed(future_to_chunk), 1):
            chunk = future_to_chunk[future]
            try:
                result = future.result()
                # Attach classification fields directly into the chunk
                chunk.update({
                    "category": result.get("category", "Unknown"),
                    "confidence": result.get("confidence", 0.0),
                    "rationale": result.get("rationale", ""),
                })
                enriched_chunks.append(chunk)
                print(f"[✓] Classified {i}/{len(chunks)} → {result.get('category', 'Unknown')} ({round(result.get('confidence', 0.0)*100, 1)}%)")
            except Exception as e:
                print(f"[✗] Error processing {chunk.get('chunk_id')}: {e}")
                # fallback if classification fails
                chunk.update({
                    "category": "Unknown",
                    "confidence": 0.0,
                    "rationale": f"Error: {e}"
                })
                enriched_chunks.append(chunk)

    print(f"[⏳] Starting batch embeddings for {len(enriched_chunks)} chunks at {datetime.utcnow().isoformat()} UTC")
    rationale_vec  = [c.get("rationale", "") for c in enriched_chunks]
    summary_vec  = [c.get("summary_text", "") for c in enriched_chunks]

    vectorsR = embed_text_batch(rationale_vec)
    vectorsS = embed_text_batch(summary_vec)
    vectorsR = np.array(vectorsR)
    vectorsS = np.array(vectorsS)
    final_vec = 0.7 * vectorsR + 0.3* vectorsS

    for chunk, vector in zip(enriched_chunks, final_vec):
        chunk["summary_vector"] = vector
    print(f"[✅] Finished batch embeddings at {datetime.utcnow().isoformat()} UTC")

    return enriched_chunks


# -------------------------
# Step 3: Create chunk index if missing
# -------------------------
def save_classifications_to_elasticsearch(classified_chunks: list, es: Elasticsearch, index: str = "employee_classifications"):
    if not es.indices.exists(index=index):
        es.indices.create(
            index=index,
            body={
                "mappings": {
                    "properties": {
                        "employee_id": {"type": "keyword"},
                        "chunk_id": {"type": "keyword"},
                        "start_time": {"type": "date"},
                        "end_time": {"type": "date"},
                        "window": {"type": "keyword"},
                        "dominant_event": {"type": "keyword"},
                        "summary_text": {"type": "text"},
                        "event_count": {"type": "integer"},
                        "quality_score": {"type": "float"},
                        "category": {"type": "keyword"},
                        "confidence": {"type": "float"},
                        "rationale": {"type": "text"},
                        "summary_vector": {
                            "type": "dense_vector",
                            "dims": 768,
                            "index": True,
                            "similarity": "cosine"
                        }
                    }
                }
            }
        )
        print(f"Created index '{index}'.")

    for chunk in classified_chunks:
        doc = {
            "employee_id": chunk.get("employee_id", chunk.get("events", [{}])[0].get("raw", {}).get("employee_id", "unknown")),
            "chunk_id": chunk.get("chunk_id"),
            "start_time": chunk.get("start_time"),
            "end_time": chunk.get("end_time"),
            "window": chunk.get("window"),
            "dominant_event": chunk.get("meta", {}).get("dominant_event", "unknown"),
            "summary_text": chunk.get("summary_text", ""),
            "event_count": chunk.get("meta", {}).get("original_event_count", 0),
            "quality_score": chunk.get("meta", {}).get("quality", {}).get("quality_score", 0.0),
            "summary_vector": chunk.get("summary_vector", []),
            "category": chunk.get("category", "Unknown"),
            "confidence": chunk.get("confidence", 0.0),
            "rationale": chunk.get("rationale", "")
        }
        es.index(index=index, id=doc["chunk_id"], document=doc)

    print(f"Saved {len(classified_chunks)} classified chunks to '{index}'.")
