import json
import time
import requests
from datetime import datetime
from elasticsearch import Elasticsearch
from typing import List, Dict, Any

# Ollama configuration
OLLAMA_MODEL = "llama3.2:latest"
OLLAMA_URL = "http://localhost:11434/api/generate"  # correct endpoint

# Elasticsearch client
ES = Elasticsearch("http://localhost:9200")
ES_INDEX = "employee_daily_summaries"

# -------------------------
# JSON parser helper
# -------------------------
def parse_json_response(resp_text: str) -> dict:
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
    return {"summary": "Failed to parse JSON", "activities": {}, "insights": []}


# -------------------------
# Summarization
# -------------------------
def summarize_day(chunks: List[Dict[str, Any]], employee_id: str, date: str, retries: int = 3) -> Dict[str, Any]:
    """Generate a detailed daily report with bullet points and insights."""
    if not chunks:
        return {
            "employee_id": employee_id,
            "date": date,
            "summary": "No chunks available for summarization.",
            "activities": {},
            "insights": [],
        }

    # Prepare text context: category + normalized description
    joined_text = "\n".join([
        f"Category: {c.get('category', 'Unknown')}\nStart: {c.get('start_time')}\nEnd: {c.get('end_time')}\nSummary: {c.get('summary_text', '')}" 
        for c in chunks
    ])[:15000]


    prompt = f"""
You are an expert productivity analyst. Summarize the employee's full-day activity log.

Instructions:
Generate a professional daily report that includes:
1. **Executive Summary** (2-3 sentences of key accomplishments)
2. Provide a concise **Daily Overview** paragraph.
3. For **Detailed Activity Breakdown**, group activities by category.
   - Under each category, create bullet points describing **meaningful tasks or actions performed**
4. For **Insights & Observations**, note patterns, context switches, highlights or anomalies.
5. Do NOT just repeat category names; extract actual activities from the summaries.

Return valid JSON:
{{
  "date": "{date}",
  "employee_id": "{employee_id}",
  "summary": str,
  "activities": {{category: [points]}},
  "insights": [points],
  "chunk_ids": [list of chunk_id strings used]
}}

Employee Logs:
{joined_text}
"""


    for attempt in range(retries):
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "options": {"temperature": 0.3},
                "stream": False,
            }
            resp = requests.post(OLLAMA_URL, json=payload, timeout=240)
            resp.raise_for_status()
            response_text = resp.json().get("response", "").strip()
            result = parse_json_response(response_text)

            # Attach metadata
            result.update({
                "employee_id": employee_id,
                "date": date,
                "generated_at": datetime.utcnow().isoformat(),
                "chunk_ids": [c.get("chunk_id") for c in chunks],
            })
            return result

        except Exception as e:
            print(f"[summarize_day] Error: {e}. Retry {attempt+1}/{retries}...")
            time.sleep(3)

    # fallback summary
    return {
        "employee_id": employee_id,
        "date": date,
        "summary": "Failed to generate summary after retries.",
        "activities": {},
        "insights": [],
        "chunk_ids": [c.get("chunk_id") for c in chunks],
    }


# -------------------------
# Elasticsearch save
# -------------------------
def save_summary_to_es(summary: Dict[str, Any]):
    """Save the generated summary to Elasticsearch."""
    try:
        doc_id = f"{summary['employee_id']}_{summary['date']}"
        ES.index(index=ES_INDEX, id=doc_id, document=summary)
        print(f"[save_summary_to_es] Summary saved for {summary['employee_id']} - {summary['date']}")
    except Exception as e:
        print(f"[save_summary_to_es] Failed: {e}")


# -------------------------
# High-level function
# -------------------------
def summarize_and_store(chunks: List[Dict[str, Any]], employee_id: str, date: str):
    """Summarize chunks and persist the result."""
    summary = summarize_day(chunks, employee_id, date)
    save_summary_to_es(summary)
    return summary
////////////////////
import json
import time
import requests
from datetime import datetime
from elasticsearch import Elasticsearch
from typing import List, Dict, Any

# Ollama configuration
OLLAMA_MODEL = "llama3.2:latest"
OLLAMA_URL = "http://localhost:11434/api/generate"  # correct endpoint

# Elasticsearch client
ES = Elasticsearch("http://localhost:9200")
ES_INDEX = "employee_daily_summaries"

# -------------------------
# JSON parser helper
# -------------------------
def parse_json_response(resp_text: str) -> dict:
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
    return {"summary": "Failed to parse JSON", "activities": {}, "insights": []}


# -------------------------
# Summarization
# -------------------------
def summarize_day(chunks: List[Dict[str, Any]], employee_id: str, date: str, retries: int = 3) -> Dict[str, Any]:
    """Generate a detailed daily report with bullet points and insights."""
    if not chunks:
        return {
            "employee_id": employee_id,
            "date": date,
            "summary": "No chunks available for summarization.",
            "activities": {},
            "insights": [],
        }

    # Prepare text context: category + normalized description
    joined_text = "\n".join([
        f"Category: {c.get('category', 'Unknown')}\nStart: {c.get('start_time')}\nEnd: {c.get('end_time')}\nSummary: {c.get('summary_text', '')}" 
        for c in chunks
    ])[:15000]


    prompt = f"""
You are an expert productivity analyst. Summarize the employee's full-day activity log.

Instructions:
Generate a professional daily report that includes:

1. **Executive Summary**: 2-3 sentences highlighting the employee’s key accomplishments and focus areas.
2. **Daily Overview**: 1 paragraph summarizing overall productivity, focus, and work patterns.
3. **Detailed Activity Breakdown**:
   - Group activities by category.
   - Under each category, create bullet points describing **meaningful tasks or actions performed**, based on the detailed events (keystrokes, window switches, shortcuts).
4. **Insights & Observations**:
   - Highlight context switches, distractions, anomalies, or patterns that could improve productivity.
5. **Do not just repeat category names. Extract the meaningful actions from the logs**.

Return valid JSON (strictly parsable):
{
  "date": "{date}",
  "employee_id": "{employee_id}",
  "summary": "<Executive Summary + Daily Overview combined if needed>",
  "activities": {
    "Development": ["", ""],
    "Browsing/Distraction": ["", ""]
  },
  "insights": ["", ""],
  "chunk_ids": ["chunk_id_1", "chunk_id_2", "..."]
}

Employee Logs (include all categories, start/end times, and summary_text):
{joined_text}
"""


    for attempt in range(retries):
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "options": {"temperature": 0.3},
                "stream": False,
            }
            resp = requests.post(OLLAMA_URL, json=payload, timeout=240)
            resp.raise_for_status()
            response_text = resp.json().get("response", "").strip()
            result = parse_json_response(response_text)

            # Attach metadata
            result.update({
                "employee_id": employee_id,
                "date": date,
                "generated_at": datetime.utcnow().isoformat(),
                "chunk_ids": [c.get("chunk_id") for c in chunks],
            })
            return result

        except Exception as e:
            print(f"[summarize_day] Error: {e}. Retry {attempt+1}/{retries}...")
            time.sleep(3)

    # fallback summary
    return {
        "employee_id": employee_id,
        "date": date,
        "summary": "Failed to generate summary after retries.",
        "activities": {},
        "insights": [],
        "chunk_ids": [c.get("chunk_id") for c in chunks],
    }


# -------------------------
# Elasticsearch save
# -------------------------
def save_summary_to_es(summary: Dict[str, Any]):
    """Save the generated summary to Elasticsearch."""
    try:
        doc_id = f"{summary['employee_id']}_{summary['date']}"
        ES.index(index=ES_INDEX, id=doc_id, document=summary)
        print(f"[save_summary_to_es] Summary saved for {summary['employee_id']} - {summary['date']}")
    except Exception as e:
        print(f"[save_summary_to_es] Failed: {e}")


# -------------------------
# High-level function
# -------------------------
def summarize_and_store(chunks: List[Dict[str, Any]], employee_id: str, date: str):
    """Summarize chunks and persist the result."""
    summary = summarize_day(chunks, employee_id, date)
    save_summary_to_es(summary)
    return summary
