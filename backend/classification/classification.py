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
OLLAMA_URL = "http://localhost:11434"  # replace with your Ollama endpoint
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
    start = time.time()  # start timer
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

**DECISION RULES:**
- If multiple tools are used, classify by PRIMARY INTENT (e.g., browsing docs while coding = Development)
- Browser usage is Research if visiting work docs/Stack Overflow WITH context of a work task
- Browser usage is Distraction if visiting social media, news, entertainment sites
- Rapid app switching (<10 sec) without meaningful actions suggests context confusion - be cautious
- Idle periods >5 minutes should be Idle/Break even if app is open

**YOUR TASK:**

Metadata:
- Dominant event: {dominant_event}
- Event count: {event_count}
- Window/application: {window}
- Chunk duration: from {start_time} to {end_time}
- Quality score: {chunk.get('meta', {}).get('quality', {}).get('quality_score', 'unknown')}
- Unique apps: {chunk.get('meta', {}).get('quality', {}).get('unique_apps', 0)}

Chunk Summary:
{text}

Return ONLY valid JSON:
{{"category": str, "confidence": float (0.0-1.0), "rationale": str}}

Rationale format: "Action: [what was done], Tools: [apps/files used], Context: [work context], Intent: [primary goal]"
IMPORTANT: Do NOT include any text outside the JSON object.
"""

    for attempt in range(retries):
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
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
                    if any(k in text_lower for k in ["stackoverflow", "developer.huawei", "docs.huawei", "tutorial", "documentation"]):
                        category = "Research / Learning"

                    elif any(k in text_lower for k in ["facebook", "youtube", "instagram", "netflix", "reddit", "twitter", "personal email", "news site", "entertainment"]):
                        category = "Browsing / Distraction"

                    elif any(k in text_lower for k in ["code", "visual studio", "pycharm", "intellij", "vscode", "sublime", "notepad++", "git", ".py", ".java", ".js", ".cpp", "commit", "debug"]):
                        category = "Development / Coding"

                    elif any(k in text_lower for k in ["terminal", "bash", "shell", "cmd", "powershell", "ssh", "server", "log analysis", "error fix", "monitoring", "alert"]):
                        category = "System Maintenance / Troubleshooting"

                    elif any(k in text_lower for k in ["welink", "teams", "outlook", "meeting", "call", "chat", "slack", "email", "zoom", "conference"]):
                        category = "Meetings / Communication"

                    elif any(k in text_lower for k in ["jira", "ticket", "report", "dashboard", "timesheet", "form", "hr portal", "admin panel"]):
                        category = "Administrative / Reporting"

                    elif any(k in text_lower for k in ["jenkins", "deploy", "pipeline", "ci/cd", "build", "kubernetes", "docker", "cloud console", "huawei cloud", "serverless", "container"]):
                        category = "Cloud Operations / DevOps"

                    elif any(k in text_lower for k in ["script", "automation", "cron", "batch", "scheduled task", "ansible", "puppet"]):
                        category = "Automation / Scripting"

                    elif any(k in text_lower for k in ["break", "idle", "afk", "lunch", "coffee", "away"]):
                        category = "Idle / Break"

                    # Multi-keyword check for generic browsers (chrome/firefox alone is ambiguous)
                    elif any(k in text_lower for k in ["chrome", "firefox", "browser"]) and any(k in text_lower for k in ["search", "google", "wikipedia", "article"]):
                        category = "Research / Learning"

                    else:
                        category = "Unknown"

                    parsed.update({
                        "category": category,
                        "confidence": 0.35,  # Lower confidence for heuristics
                        "rationale": parsed.get("rationale", "") + f" [Heuristic fallback: matched keywords for {category}]"
                    })
            end = time.time()  # end timerP
            elapsed = end - start
            print(f"[classify_activity] ⏱ Chunk {chunk.get('chunk_id', '?')} classified in {elapsed:.2f} seconds")
            return parsed
        except Exception as e:
            print(f"[classify_activity] Error: {e}. Retry {attempt+1}/{retries}...")
            time.sleep(2)
    end = time.time()
    print(f"[classify_activity] ❌ Chunk {chunk.get('chunk_id', '?')} failed after {end - start:.2f} seconds")
    return {"category": "Unknown", "confidence": 0.0, "rationale": "Failed after retries."}
# -------------------------
# Embedding
# -------------------------

from sentence_transformers import SentenceTransformer
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
# Load embedding model
embedding_model = SentenceTransformer(EMBEDDING_MODEL)

def embed_text_batch(texts: List[str], show_progress: bool = False) -> np.ndarray:
    if not texts:
        return np.array([])
    
    valid_texts = [t if t.strip() else "[empty]" for t in texts]

    embeddings = embedding_model.encode(
        valid_texts, 
        convert_to_numpy=True,
        normalize_embeddings=True,  
        show_progress_bar=show_progress,
        batch_size=32
    )

    return embeddings


# -------------------------
# Batch Classification
# -------------------------


def batch_classify_parallel(chunks: List[Dict[str, Any]], max_workers: int = MAX_WORKERS) -> List[Dict[str, Any]]:
    """Run classification for many chunks in parallel and attach results to each chunk."""
    batch_start = time.time()
    enriched_chunks = []
    inference_times = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_chunk = {executor.submit(classify_activity, chunk): chunk for chunk in chunks}
        for i, future in enumerate(as_completed(future_to_chunk), 1):
            chunk = future_to_chunk[future]
            try:
                classify_start = time.time()

                result = future.result()
                classify_end = time.time()

                inference_times.append(classify_end - classify_start)
                # Attach classification fields directly into the chunk
                chunk.update({
                    "category": result.get("category", "Unknown"),
                    "confidence": result.get("confidence", 0.0),
                    "rationale": result.get("rationale", ""),
                })
                try:
                    start_dt = datetime.fromisoformat(chunk.get("start_time", ""))
                    end_dt = datetime.fromisoformat(chunk.get("end_time", ""))
                    duration_minutes = round((end_dt - start_dt).total_seconds() / 60, 1)
                    chunk["duration"] = duration_minutes
                except Exception:
                    chunk["duration"] = None

                enriched_chunks.append(chunk)
                print(f"[✓] Classified {i}/{len(chunks)} → {result.get('category', 'Unknown')} ({round(result.get('confidence', 0.0)*100, 1)}%) | {chunk.get('duration', '?')} min")                
            except Exception as e:
                print(f"[✗] Error processing {chunk.get('chunk_id')}: {e}")
                # fallback if classification fails
                chunk.update({
                    "category": "Unknown",
                    "confidence": 0.0,
                    "rationale": f"Error: {e}"
                })
                enriched_chunks.append(chunk)
    batch_end = time.time()
    total_time = batch_end - batch_start
    avg_inference_time = np.mean(inference_times) if inference_times else 0
    throughput = (len(chunks) / total_time) * 60 if total_time > 0 else 0
    print(f"[batch_classify_parallel] ⏱ Completed parallel classification for {len(chunks)} chunks in {batch_end - batch_start:.2f} seconds")
    print("\n📊 --- Classification Performance Metrics ---")
    print(f"  • Total chunks processed: {len(chunks)}")
    print(f"  • Average inference time: {avg_inference_time:.2f} seconds per chunk")
    print(f"  • Total wall-clock time: {total_time:.2f} seconds")
    print(f"  • Throughput: {throughput:.2f} chunks/minute with {max_workers} parallel workers")
    print("--------------------------------------------------")

    # --- Embedding ---
    embed_start = time.time()
    print(f"[⏳] Starting batch embeddings for {len(enriched_chunks)} chunks at {datetime.utcnow().isoformat()} UTC")
    rationale_texts = [c.get("rationale", "") for c in enriched_chunks]
    summary_texts  = [c.get("summary_text", "") for c in enriched_chunks]

    """ combined_vectors = embed_text_pairs_weighted(
        rationale_texts, 
        summary_texts,
        weight_a=0.7,  # Weight for rationale
        weight_b=0.3   # Weight for summary
    )
    for chunk, vector in zip(enriched_chunks, combined_vectors):
        chunk["summary_vector"] = vector
    embed_end = time.time()
    print(f"[✅] Finished batch embeddings in {embed_end - embed_start:.2f} seconds at {datetime.utcnow().isoformat()} UTC")
    """
    print("[⏳] Embedding rationales...")
    rationale_vectors = embed_text_batch(rationale_texts, show_progress=True)
    
    print("[⏳] Embedding summaries...")
    summary_vectors = embed_text_batch(summary_texts, show_progress=True)
    for chunk, rat_vec, sum_vec in zip(enriched_chunks, rationale_vectors, summary_vectors):
        chunk["rationale_vector"] = rat_vec.tolist()
        chunk["summary_vector"] = sum_vec.tolist()

    embed_end = time.time()
    print(f"[✅] Finished batch embeddings in {embed_end - embed_start:.2f} seconds")

    total_elapsed = embed_end - batch_start
    print(f"[batch_classify_parallel] ⏱ Total time for classification + embeddings: {total_elapsed:.2f} seconds")
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
                        },
                        "rationale_vector": {  
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
            "rationale": chunk.get("rationale", ""),
            "rationale_vector": chunk.get("rationale_vector", []),  # NEW

        }
        es.index(index=index, id=doc["chunk_id"], document=doc)

    print(f"Saved {len(classified_chunks)} classified chunks to '{index}'.")
