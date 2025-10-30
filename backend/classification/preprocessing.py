"""
preprocessing_enhanced.py

Enhanced preprocessing module for employee activity logs.

Changes in this version:
- Filters out unnecessary events (keeps only meaningful ones)
- Uses idle duration from idle_end (no redundant handling)
- Normalizes event aliases (e.g., "consent given to keylogger" → "consent_given")
- Slightly refines adaptive chunking and quality scoring
- Adds optional summary_text and dominant_event fields for each chunk
"""
import tiktoken  # Optional dependency
from elasticsearch import Elasticsearch
from typing import List, Dict, Any, Optional
import re
import logging
from datetime import datetime, timezone, timedelta, date
from itertools import groupby
from collections import Counter

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# -------------------------
# Configuration / Constants
# -------------------------
DEFAULT_MAX_LOGS_PER_CHUNK = 100
DEFAULT_MAX_TOKEN_APPROX = 1000
DEFAULT_SLICE_MINUTES = 20
MIN_CHUNK_SIZE = 5
WINDOW_SWITCH_THRESHOLD_SEC = 180  


KEY_MAP = {
    "ctrl_l": "Ctrl", "ctrl_r": "Ctrl", "alt_l": "Alt", "alt_r": "Alt",
    "tab": "Tab", "shift": "Shift", "enter": "Enter", "backspace": "Backspace",
    "space": "Space", "cmd": "Cmd", "up": "↑", "down": "↓", "left": "←", "right": "→"
}

# Keep only these event types for analysis
RELEVANT_EVENTS = {
    "keystrokes", "clipboard_paste", "window_switch", "shortcut",
    "idle_start", "idle_end", "pause", "resume"
}


# Event aliases normalization
EVENT_ALIASES = {
    "consent given to keylogger": "consent_given",
    "idleend": "idle_end",
    "idlestart": "idle_start",
}

# -------------------------
# Timestamp & Date helpers
# -------------------------
def parse_timestamp(ts: Any) -> Optional[datetime]:
    """Parse timestamp inputs to timezone-aware UTC datetimes."""
    if ts is None:
        return None

    if isinstance(ts, (int, float)):
        try:
            val = float(ts)
            if val > 1e12:
                val = val / 1000.0
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except Exception:
            return None

    if isinstance(ts, str):
        s = ts.strip()
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            pass

        if re.fullmatch(r"\d+", s):
            try:
                iv = int(s)
                if iv > 1e12:
                    iv = iv // 1000
                return datetime.fromtimestamp(iv, tz=timezone.utc)
            except Exception:
                return None

        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S"):
            try:
                dt = datetime.strptime(s, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                continue
    return None


def normalize_date(date_input: Any) -> date:
    """Return a datetime.date from various inputs."""
    if isinstance(date_input, date) and not isinstance(date_input, datetime):
        return date_input
    if isinstance(date_input, datetime):
        return date_input.date()
    if isinstance(date_input, str):
        try:
            return datetime.strptime(date_input.split(" ")[0], "%Y-%m-%d").date()
        except Exception as e:
            raise ValueError(f"Unsupported date string: {date_input}") from e
    raise ValueError(f"Unsupported date type: {type(date_input)}")

# -------------------------
# Text helpers
# -------------------------
def truncate_text(text: Optional[str], max_len: int = 200) -> str:
    if not text:
        return ""
    text = str(text)
    if len(text) <= max_len:
        return text
    return text[:100] + " ... " + text[-100:]


def fmt_dur(seconds: float) -> str:
    if not seconds or seconds <= 0:
        return "0s"
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    m = secs // 60
    s = secs % 60
    return f"{m}m {s}s"

# -------------------------
# Key parsing & collapsing
# -------------------------
def parse_keys(text: str) -> List[str]:
    keys = re.findall(r"<Key\.([a-zA-Z0-9_]+)>", text)
    mapped = [KEY_MAP.get(k.lower(), k) for k in keys]
    return mapped


def collapse_repeats(keys: List[str]) -> List[str]:
    collapsed: List[str] = []
    for key, group in groupby(keys):
        group_list = list(group)
        count = len(group_list)
        if count > 4:
            collapsed.append(f"{key} (x{count})")
        else:
            collapsed.extend(group_list)
    return collapsed

# -------------------------
# Event normalization
# -------------------------
def normalize_event(log: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Convert raw log dict into normalized event dict or None if invalid or irrelevant."""
    ts = parse_timestamp(log.get("timestamp"))
    if ts is None:
        return None

    event_type = str(log.get("event", "unknown")).lower().strip()
    event_type = EVENT_ALIASES.get(event_type, event_type)

    # Filter out irrelevant events
    if event_type not in RELEVANT_EVENTS:
        return None

    app = str(log.get("application", "unknown")).replace(".exe", "")
    window = str(log.get("window", "unknown"))
    text = str(log.get("text", ""))
    control = str(log.get("control", ""))
    session_id = str(log.get("session_id", "unknown"))
    seq_num = int(log.get("seq_num", 0)) if str(log.get("seq_num", "")).isdigit() else 0

    normalized: Dict[str, Any] = {
        "timestamp": ts,
        "event": event_type,
        "application": app,
        "window": window,
        "description": "",
        "start_time": ts,
        "end_time": ts,
        "duration_sec": 0.0,
        "session_id": session_id,
        "seq_num": seq_num,
        "raw": log,
    }

    if event_type == "keystrokes":
        keys = parse_keys(text)
        clean_text = re.sub(r"<Key\.[^>]+>", "", text).strip()
        backspaces = sum(1 for k in keys if k.lower() == "backspace")
        desc_parts: List[str] = []
        if clean_text:
            desc_parts.append(f"typed: '{truncate_text(clean_text)}'")
        if backspaces:
            desc_parts.append(f"deleted {backspaces} chars")
        if keys and not clean_text:
            desc_parts.append("pressed " + "+".join(collapse_repeats(keys)))
        normalized["description"] = "; ".join(desc_parts) if desc_parts else "No meaningful keystrokes"
        normalized["duration_sec"] = max((len(clean_text) + len(keys)) * 0.12, 0.4)
        normalized["end_time"] = ts + timedelta(seconds=normalized["duration_sec"])

    elif event_type == "clipboard_paste":
        preview = truncate_text(text, 200)
        normalized["description"] = f"Pasted content: {preview}" if preview else "Empty paste"
        normalized["duration_sec"] = 1.5 + len(text) / 2000.0
        normalized["end_time"] = ts + timedelta(seconds=normalized["duration_sec"])

    elif event_type == "window_switch":
        normalized["description"] = f"Switched to {app} ({window})"
        normalized["duration_sec"] = 0.5
        normalized["end_time"] = ts + timedelta(seconds=0.5)

    elif event_type == "shortcut":
        shortcut_name = log.get("shortcut_name", "")
        normalized["description"] = f"Used shortcut: {shortcut_name}" if shortcut_name else "Used shortcut"
        normalized["duration_sec"] = 0.4
        normalized["end_time"] = ts + timedelta(seconds=0.4)

    elif event_type == "idle_start":
        normalized["description"] = f"Went idle in {app} ({window})"
        normalized["duration_sec"] = 0.0

    elif event_type == "idle_end":
        dur = max(float(log.get("idle_duration_sec", 0)), 0.0)
        normalized["description"] = f"Returned from idle (away {fmt_dur(dur)})"
        normalized["duration_sec"] = dur
        normalized["end_time"] = ts + timedelta(seconds=dur)

    elif event_type == "pause":
        reason = str(log.get("reason", "unspecified"))
        dur = max(float(log.get("duration_minutes", 0)) * 60, 0.0)
        normalized["description"] = f"Paused work ({reason}, {fmt_dur(dur)})"
        normalized["duration_sec"] = dur
        normalized["end_time"] = ts + timedelta(seconds=dur)
    elif event_type == "resume":
        normalized["description"] = "Resumed activity after pause"
        normalized["duration_sec"] = 0.2
        normalized["end_time"] = ts + timedelta(seconds=0.2)
    return normalized

# -------------------------
# Chunk quality assessment
# -------------------------
def assess_chunk_quality(chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not chunk:
        return {"quality_score": 0.0, "sufficient_data": False, "event_count": 0, "char_count": 0, "unique_apps": 0, "has_meaningful_content": False}

    event_count = len(chunk)
    char_count = sum(len(e.get("description", "")) for e in chunk)
    apps = set(e.get("application", "unknown") for e in chunk if e.get("application"))
    meaningful_events = sum(1 for e in chunk if e.get("description", "").startswith(("typed:", "Pasted content:")) or e.get("event") in ("window_switch", "shortcut"))
    repetitive_events = sum(1 for e in chunk if "(x" in e.get("description", "") or re.match(r"typed: '\.'", e.get("description", "")))
    quality_score = (
        (0.35 if meaningful_events > 0 else 0.0)
        + min(event_count / 12, 1.0) * 0.25
        + min(char_count / 600, 1.0) * 0.25
        + min(len(apps) / 3, 1.0) * 0.15
        - min(repetitive_events / 10, 0.3)  # Penalize noise
    )

    return {
        "quality_score": round(quality_score, 3),
        "sufficient_data": quality_score > 0.35 and meaningful_events >= 2,
        "event_count": event_count,
        "char_count": char_count,
        "unique_apps": len(apps),
        "has_meaningful_content": meaningful_events > 0,
    }

# -------------------------
# Adaptive chunking
# -------------------------
def adaptive_chunk_logs(
    logs: List[Dict[str, Any]],
    max_logs: int = DEFAULT_MAX_LOGS_PER_CHUNK,
    max_tokens: int = DEFAULT_MAX_TOKEN_APPROX,
    slice_minutes: int = DEFAULT_SLICE_MINUTES,
    min_chunk_size: int = MIN_CHUNK_SIZE,
) -> List[List[Dict[str, Any]]]:
    """Chunk normalized logs into adaptive time/context-based segments."""
    normalized_events = []
    for raw in logs:
        norm = normalize_event(raw)
        if norm:
            normalized_events.append(norm)
    if not normalized_events:
        return []

    normalized_events.sort(key=lambda e: e["timestamp"])

    chunks, current = [], []
    start_time, current_window = None, None
    approx_tokens = 0

    def finalize():
        nonlocal current, approx_tokens, start_time, current_window
        if current:
            quality = assess_chunk_quality(current)
            if quality["sufficient_data"] and len(current) >= min_chunk_size:
                chunks.append(current)
        current, approx_tokens, start_time, current_window = [], 0, None, None

    for ev in normalized_events:
        ts = ev["timestamp"]
        if start_time is None:
            start_time, current_window = ts, ev.get("window")

        event_count = len(current)
        slice_adj = max(10, slice_minutes - event_count // 20)  # gradual adaptation

        # Split on idle/pause
        if ev["event"] in ("pause", "idle_start", "resume") and current:
            finalize()

        # Time-based split
        if start_time and (ts - start_time).total_seconds() > slice_adj * 60:
            finalize()
            start_time, current_window = ts, ev.get("window")

        # Window-based split
# Window-based split
        if current_window and ev.get("window") != current_window:
            if len(current) >= min_chunk_size and (ts - start_time).total_seconds() >= WINDOW_SWITCH_THRESHOLD_SEC:
                finalize()
                start_time, current_window = ts, ev.get("window")
            else:
                current_window = ev.get("window")



        current.append(ev)
        approx_tokens += max(1, len(ev.get("description", "")) // 4)

        # Token or log limit
        if len(current) >= max_logs or approx_tokens >= max_tokens:
            finalize()

    finalize()
    return chunks

# -------------------------
# Elasticsearch helpers
# -------------------------
def fetch_logs_for_employee(es, index, employee_id, date_str, size=10000):
    date_obj = normalize_date(date_str)
    start_dt = datetime.combine(date_obj, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = datetime.combine(date_obj, datetime.max.time(), tzinfo=timezone.utc)
    start_ms, end_ms = int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)

    query = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"employee_id.keyword": employee_id}},
                    {"range": {"timestamp": {"gte": start_ms, "lte": end_ms}}}
                ]
            }
        },
        "sort": [{"timestamp": {"order": "asc"}}]
    }

    resp = es.search(index=index, body=query, size=size, scroll="2m")
    scroll_id = resp.get("_scroll_id")
    hits = resp["hits"]["hits"]
    all_logs = [h["_source"] for h in hits]

    while hits:
        resp = es.scroll(scroll_id=scroll_id, scroll="2m")
        scroll_id = resp.get("_scroll_id")
        hits = resp["hits"]["hits"]
        all_logs.extend([h["_source"] for h in hits])

    es.clear_scroll(scroll_id=scroll_id)
    return all_logs

def clean_description(text: str) -> str:
    if not text:
        return ""
    # Remove non-printable characters
    text = ''.join(c for c in text if c.isprintable() or c in ' \t\n')
    # Collapse long repeated characters (e.g., "....." → ". (x5)")
    text = re.sub(r'(.)\1{4,}', lambda m: f"{m.group(1)} (x{len(m.group(0))})", text)
    # Remove modifier-only keystrokes like <ctrl_l><ctrl_r>
    text = re.sub(r'(<(?:ctrl|alt|shift)[^>]*>)+', '', text)
    # Remove leftover XML-like tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove timestamp-like strings [HH:MM:SS] or (HH:MM)
    text = re.sub(r'\[?\b\d{1,2}:\d{2}(:\d{2})?\]?', '', text)
    # Remove very short cryptic entries
    text = re.sub(r'^\w{1,3}$|^[^a-zA-Z0-9\s]{1,5}$', '', text)
    # Remove repetitive punctuation
    text = re.sub(r'([!?.,])\1{1,}', r'\1', text)
    # Custom meaningless patterns
    bad_patterns = [
        r"No meaningful keystrokes",
        r"pressed [A-Za-z+]+$",
        r"typed: '\s*'",
        r"Empty paste",
        r"^\s*$",
    ]
    for pat in bad_patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

# -------------------------
# Utility: prepare chunks & metadata
# -------------------------
def prepare_chunks_for_pipeline(
    logs: List[Dict[str, Any]],
    employee_id: Optional[str] = None,
    date_str: Optional[str] = None,
    min_quality_score: float = 0.5,

    **chunk_opts
) -> List[Dict[str, Any]]:
    """Return chunk dicts ready for LLM classification/summarization."""
    if not logs:
        return []

    # Try to auto-detect employee_id and date if not provided
    if employee_id is None:
        employee_id = logs[0].get("employee_id") or logs[0].get("raw", {}).get("employee_id", "unknown")
    if date_str is None:
        first_ts = logs[0].get("timestamp")
        if isinstance(first_ts, str):
            try:
                first_ts = datetime.fromisoformat(first_ts)
            except Exception:
                first_ts = datetime.utcnow()
        date_str = first_ts.date().isoformat() if first_ts else "unknown_date"

    # Perform chunking
    raw_chunks = adaptive_chunk_logs(logs, **chunk_opts)
    scores = [assess_chunk_quality(ch)["quality_score"] for ch in raw_chunks]
    sufficient_flags = [assess_chunk_quality(ch)["sufficient_data"] for ch in raw_chunks]
    for i, (score, suff) in enumerate(zip(scores, sufficient_flags)):
        print(f"Chunk {i}: quality_score={score:.3f}, sufficient_data={suff}")

    out: List[Dict[str, Any]] = []

    for i, ch in enumerate(raw_chunks):
        if not ch:
            continue
        start, end = ch[0]["timestamp"], ch[-1]["timestamp"]
        apps = [e.get("application", "unknown") for e in ch]
        dominant_app = max(set(apps), key=apps.count) if apps else "unknown"
        quality = assess_chunk_quality(ch)
        dominant_event = Counter(e["event"] for e in ch).most_common(1)[0][0]
        cleaned_events = []
        for e in ch:
            desc = clean_description(e.get("description", ""))
            if desc:
                cleaned_events.append(f"- [{e['timestamp'].strftime('%H:%M:%S')}] {desc}")
        last_switch_time = None
        switch_apps = []
        for e in ch:
            desc = clean_description(e.get("description", ""))
            if e["event"] == "window_switch" and last_switch_time:
                if (e["timestamp"] - last_switch_time).total_seconds() < 10:
                    switch_apps.append(e["application"])
                    continue
                else:
                    if len(switch_apps) > 1:
                        cleaned_events.append(f"- [{last_switch_time.strftime('%H:%M:%S')}] Toggled between {', '.join(set(switch_apps))}")
                    switch_apps = [e["application"]]
            elif e["event"] == "window_switch":
                switch_apps = [e["application"]]
                last_switch_time = e["timestamp"]
            else:
                if switch_apps:
                    if len(switch_apps) > 1:
                        cleaned_events.append(f"- [{last_switch_time.strftime('%H:%M:%S')}] Toggled between {', '.join(set(switch_apps))}")
                    switch_apps = []
                if desc:
                    cleaned_events.append(f"- [{e['timestamp'].strftime('%H:%M:%S')}] {desc}")
        if switch_apps and len(switch_apps) > 1:
            cleaned_events.append(f"- [{last_switch_time.strftime('%H:%M:%S')}] Toggled between {', '.join(set(switch_apps))}")
        summary_text = "\n".join(cleaned_events)
        try:
            enc = tiktoken.get_encoding("cl100k_base")
            token_count = len(enc.encode(summary_text))
        except ImportError:
            token_count = len(summary_text) // 4 + len(ch)  # Fallback: ~4 chars/token + event count
        if token_count > 2000:
            cleaned_events = cleaned_events[:len(cleaned_events)//2]
            summary_text = "\n".join(cleaned_events) + "\n[Truncated due to length]"
            token_count = min(token_count, 2000)  # Recalculate or cap
        chunk_id = f"{employee_id}_{date_str}_chunk_{i}"


        chunk_id = f"{employee_id}_{date_str}_chunk_{i}"

        out.append({
            "employee_id": employee_id,
            "chunk_date": date_str,
            "chunk_id": chunk_id,
            "events": ch,
            "window": dominant_app,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "summary_text": summary_text,
            "meta": {
                "original_event_count": len(ch),
                "quality": quality,
                "dominant_event": dominant_event,
                "dominant_app": dominant_app,
                "temporal_span_minutes": round((end - start).total_seconds() / 60, 2),
                "approx_tokens": token_count,


            }
        })
    out = [
        c for c in out 
        if c["meta"]["quality"]["sufficient_data"] and 
           c["meta"]["quality"]["quality_score"] >= min_quality_score
    ]
    return out

# -------------------------
# Elasticsearch saving utility
# -------------------------

def save_chunks_to_elasticsearch(chunks: list, es: Elasticsearch, index: str = "employee_chunks2"):
    """
    Save preprocessed chunks to Elasticsearch.
    
    Args:
        chunks (list): List of chunks from prepare_chunks_for_pipeline()
        es (Elasticsearch): Elasticsearch client instance
        index (str): Index name to store chunks
    """
    # Create index if it doesn't exist
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
                        "events": {"type": "nested"}
                    }
                }
            }
        )

    # Index each chunk
    for chunk in chunks:
        doc = {
            "employee_id": chunk["employee_id"], 
            "chunk_id": chunk.get("chunk_id"),
            "start_time": chunk.get("start_time"),
            "end_time": chunk.get("end_time"),
            "window": chunk.get("window"),
            "dominant_event": chunk.get("meta", {}).get("dominant_event", "unknown"),
            "summary_text": chunk.get("summary_text", ""),
            "event_count": chunk.get("meta", {}).get("original_event_count", 0),
            "quality_score": chunk.get("meta", {}).get("quality", {}).get("quality_score", 0.0),
            "events": chunk.get("events", [])
        }
        es.index(index=index, id=doc["chunk_id"], document=doc)
    print(f"Saved {len(chunks)} chunks to Elasticsearch index '{index}'.")
