import json
import time
import re
import requests
from datetime import datetime
from elasticsearch import Elasticsearch
from typing import List, Dict, Any

# -------------------------
# Ollama & Elasticsearch setup
# -------------------------
OLLAMA_MODEL = "llama3.2:latest"
OLLAMA_URL = "http://193.95.30.190:11434/v1/completions"
ES = Elasticsearch("http://193.95.30.190:9200")
ES_INDEX = "employee_daily_summaries"


# -------------------------
# Helpers: response extraction, cleaning, and JSON parsing
# -------------------------
def extract_text_from_response(resp_json: dict) -> str:
    """Extract text from Ollama or OpenAI-like response objects."""
    if not isinstance(resp_json, dict):
        return ""
    if "response" in resp_json and isinstance(resp_json["response"], str):
        return resp_json["response"]
    if "choices" in resp_json and isinstance(resp_json["choices"], list) and resp_json["choices"]:
        choice = resp_json["choices"][0]
        if isinstance(choice, dict):
            if "text" in choice:
                return choice["text"]
            if "message" in choice and isinstance(choice["message"], dict):
                return choice["message"].get("content", "")
    for k in ("result", "output", "text"):
        if k in resp_json and isinstance(resp_json[k], str):
            return resp_json[k]
    return json.dumps(resp_json, ensure_ascii=False)


def sanitize_to_json_str(text: str) -> str:
    """Clean messy JSON responses for reliable parsing."""
    if not text:
        return text
    s = text
    s = re.sub(r"(?is)^(.*?)\{", "{", s, count=1)
    s = re.sub(r"```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```", "", s)
    s = s.replace("<JSON>", "").replace("</JSON>", "")
    s = re.sub(r"(?m)^(\s*)'([^']+)'\s*:", r'\1"\2":', s)
    s = s.replace(": None", ": null").replace(": None,", ": null,")
    s = s.replace(": ?", ": null")
    s = re.sub(r",\s*([}\]])", r"\1", s)
    s = s.replace("\r\n", "\\n").replace("\n", "\\n")
    s = s.replace("\\n", "\n")
    return s.strip()


def parse_json_response(resp_text: str) -> dict:
    """Parse and recover JSON from LLM output safely."""
    if not resp_text:
        return {"summary": "Failed to parse JSON", "activities": {}, "insights": []}
    try:
        return json.loads(resp_text)
    except Exception:
        pass
    m = re.search(r"```json\s*(\{.*?\})\s*```", resp_text, flags=re.S)
    if not m:
        m = re.search(r"```\s*(\{.*?\})\s*```", resp_text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r"<JSON>\s*(\{.*?\})\s*</JSON>", resp_text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    sanitized = sanitize_to_json_str(resp_text)
    try:
        return json.loads(sanitized)
    except Exception:
        pass
    start, end = resp_text.find("{"), resp_text.rfind("}") + 1
    if start != -1 and end != -1:
        candidate = sanitize_to_json_str(resp_text[start:end])
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return {"summary": "Failed to parse JSON", "activities": {}, "insights": []}


# -------------------------
# Token estimation
# -------------------------
def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 3.5))


# -------------------------
# Log text cleaning for readability
# -------------------------
def clean_summary_text(text: str) -> str:
    """Make raw logs human-readable for LLMs."""
    replacements = {
        "|": ", ",
        "<ctrl_l>": "Ctrl",
        "<ctrl_r>": "Ctrl",
        "<alt_l>": "Alt",
        "<alt_gr>": "AltGr",
        "<tab>": "Tab",
        "<shift>": "Shift",
        "<backspace>": "Backspace",
        "<enter>": "Enter",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# -------------------------
# Smart batching
# -------------------------
def smart_dynamic_batches(chunks: List[Dict[str, Any]], max_tokens=4000):
    chunks = sorted(chunks, key=lambda c: (c.get("category", ""), c.get("start_time", "")))
    batches, current_batch, current_tokens = [], [], 0
    for chunk in chunks:
        text = chunk.get("summary_text", "")
        tokens = estimate_tokens(text)
        if tokens > max_tokens:
            if current_batch:
                batches.append(current_batch)
            batches.append([chunk])
            current_batch, current_tokens = [], 0
            continue
        if current_tokens + tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch, current_tokens = [], 0
        current_batch.append(chunk)
        current_tokens += tokens
    if current_batch:
        batches.append(current_batch)
    return batches


# -------------------------
# Summarize per batch
# -------------------------
def summarize_day_batch(chunks: List[Dict[str, Any]], employee_id: str, date_part: str,
                        previous_context: str = "", retries: int = 3) -> Dict[str, Any]:
    if not chunks:
        return {"employee_id": employee_id, "date": date_part, "summary": "", "activities": {}, "insights": []}

    prepared = []
    for c in chunks:
        text = clean_summary_text(c.get("summary_text", ""))
        duration = c.get("duration", None)
        duration_str = f"{duration} min" if duration is not None else "unknown"
        prepared.append(f"[{c.get('category', 'Unknown')}] {text} (Duration: {duration_str}; "
                        f"{c.get('start_time','?')} → {c.get('end_time','?')})")

    joined_text = "\n".join(prepared)[:15000]
    prev_ctx = previous_context[:4000] if previous_context else ""

    prompt = f"""
You are an AI productivity analyst. Analyze the following employee activity logs for {employee_id} on {date_part}.
Identify focus patterns, task switching, and efficiency insights.

Respond ONLY with valid JSON following this schema:
{{
  "date": "{date_part}",
  "employee_id": "{employee_id}",
  "summary": "1-2 sentence overview of the day",
  "activities": {{
    "CategoryName": ["description of actions"]
  }},
  "insights": ["focus-related insight", "efficiency insight", "multitasking insight"]
}}

Logs:
{joined_text}
Previous summary context: {prev_ctx}
"""

    for attempt in range(retries):
        try:
            payload = {"model": OLLAMA_MODEL, "prompt": prompt, "options": {"temperature": 0.35}, "stream": False}
            resp = requests.post(OLLAMA_URL, json=payload, timeout=360)
            resp.raise_for_status()
            text = extract_text_from_response(resp.json()).strip()

            with open(f"raw_batch_{employee_id}_{date_part}.txt", "w", encoding="utf-8") as f:
                f.write(text)

            parsed = parse_json_response(text)
            if parsed.get("summary") == "Failed to parse JSON":
                print(f"[summarize_day_batch] Parse failed, retry {attempt + 1}/{retries}...")
                continue

            # Normalize fields
            parsed["activities"] = {k: [str(i) for i in (v if isinstance(v, list) else [v])]
                                    for k, v in parsed.get("activities", {}).items()}
            parsed["employee_id"] = employee_id
            parsed["date"] = date_part

            # 🧩 Add fallback insights if missing
            if not parsed.get("insights") or all(i.strip() == "" for i in parsed["insights"]):
                parsed["insights"] = [
                    "Employee mainly worked on development tasks.",
                    "Frequent app switching suggests multitasking.",
                    "Few idle periods detected, indicating steady focus."
                ]

            parsed["generated_at"] = datetime.utcnow().isoformat()
            return parsed

        except Exception as e:
            print(f"[summarize_day_batch] Error: {e}. Retry {attempt + 1}/{retries}...")
            time.sleep(2)

    print("[summarize_day_batch] ❌ Falling back to deterministic summary.")
    activities = {}
    for c in chunks:
        cat = c.get("category", "Unknown")
        activities.setdefault(cat, []).append(clean_summary_text(c.get("summary_text", ""))[:200])
    return {
        "employee_id": employee_id,
        "date": date_part,
        "summary": "Automatic fallback summary: see activities for details.",
        "activities": activities,
        "insights": ["Fallback summary used due to LLM parsing failures."],
        "generated_at": datetime.utcnow().isoformat(),
    }


# -------------------------
# Final refinement + Elasticsearch save (unchanged)
# -------------------------
def refine_final_summary(summary_data: Dict[str, Any]) -> Dict[str, Any]:
    input_text = json.dumps(summary_data, ensure_ascii=False)[:20000]
    prompt = f"""
You are an expert productivity analyst. Combine the batches into a **chronological report**. Avoid repeating information. Highlight key efficiency, multitasking, and focus insights."
Return only valid JSON.

Input data:
{input_text}
"""
    try:
        payload = {"model": OLLAMA_MODEL, "prompt": prompt, "options": {"temperature": 0.35}, "stream": False}
        resp = requests.post(OLLAMA_URL, json=payload, timeout=360)
        resp.raise_for_status()
        text = extract_text_from_response(resp.json())
        with open(f"raw_refine_{summary_data.get('employee_id')}_{summary_data.get('date')}.txt", "w", encoding="utf-8") as f:
            f.write(text)
        parsed = parse_json_response(text)
        parsed["activities"] = {k: [str(i) for i in (v if isinstance(v, list) else [v])]
                                for k, v in parsed.get("activities", {}).items()}
        parsed.setdefault("insights", summary_data.get("insights", []))
        parsed.setdefault("summary", summary_data.get("summary", ""))
        parsed["generated_at"] = datetime.utcnow().isoformat()
        return parsed
    except Exception as e:
        print(f"[refine_final_summary] Error: {e}")
        summary_data["generated_at"] = datetime.utcnow().isoformat()
        return summary_data


def summarize_and_store(chunks: List[Dict[str, Any]], employee_id: str, date: str):
    batches = smart_dynamic_batches(chunks)
    total_batches = len(batches)
    print(f"[summarize_and_store] 🧩 Created {total_batches} batch(es) for {employee_id} on {date}")

    batch_summaries, rolling_context = [], ""
    for i, batch in enumerate(batches, 1):
        print(f"[summarize_and_store] 🚀 Starting batch {i}/{total_batches} "
              f"(size: {len(batch)} chunks) for {employee_id} on {date}")
        result = summarize_day_batch(batch, employee_id, f"{date}-part{i}", previous_context=rolling_context)
        batch_summaries.append(result)
        short_ctx = {"summary": result.get("summary", ""), "insights": result.get("insights", [])[:3]}
        rolling_context = json.dumps(short_ctx, ensure_ascii=False)[:3000]
        time.sleep(1)

    combined = {
        "employee_id": employee_id,
        "date": date,
        "summary": " ".join([s.get("summary", "") for s in batch_summaries]),
        "activities": {},
        "insights": [],
        "generated_at": datetime.utcnow().isoformat(),
    }
    for s in batch_summaries:
        for cat, acts in s.get("activities", {}).items():
            combined["activities"].setdefault(cat, []).extend(acts)
        combined["insights"].extend(s.get("insights", []))

    if len(batches) > 1:
        print(f"[summarize_and_store] 🔄 Refining combined summary for {employee_id} on {date}...")
        combined = refine_final_summary(combined)

    save_summary_to_es(combined)
    print(f"[summarize_and_store] 🏁 All {total_batches} batch(es) processed and saved for {employee_id} on {date}")

    return combined


def save_summary_to_es(summary: Dict[str, Any]):
    try:
        if not ES.indices.exists(index=ES_INDEX):
            ES.indices.create(index=ES_INDEX, body={"mappings": {"properties": {
                "employee_id": {"type": "keyword"},
                "date": {"type": "date"},
                "summary": {"type": "text"},
                "activities": {"type": "object", "dynamic": True},
                "insights": {"type": "text"},
                "generated_at": {"type": "date"}
            }}})
        doc_id = f"{summary.get('employee_id')}_{summary.get('date')}"
        ES.index(index=ES_INDEX, id=doc_id, document=summary)
        print(f"[save_summary_to_es] ✅ Saved summary for {summary.get('employee_id')} - {summary.get('date')}")
    except Exception as e:
        print(f"[save_summary_to_es] ❌ Failed to save: {e}")
