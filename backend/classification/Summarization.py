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
OLLAMA_URL = "http://localhost:11434/api/generate"
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


"""def parse_json_response(resp_text: str) -> dict:
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

"""
def parse_json_response(resp_text: str) -> dict:
    """Parse and recover JSON from LLM output with aggressive extraction."""
    if not resp_text:
        return {"summary": "Empty response", "activities": {}, "insights": []}
    
    # Strategy 1: Direct parse (if model followed instructions)
    try:
        return json.loads(resp_text.strip())
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract JSON from markdown code blocks
    patterns = [
        r'```json\s*(\{.*?\})\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'<JSON>\s*(\{.*?\})\s*</JSON>',
        r'(\{[^{}]*"date"[^{}]*"summary"[^{}]*\})',  # Look for our schema
    ]
    
    for pattern in patterns:
        match = re.search(pattern, resp_text, flags=re.DOTALL)
        if match:
            try:
                candidate = sanitize_to_json_str(match.group(1))
                parsed = json.loads(candidate)
                # Validate it has required fields
                if all(k in parsed for k in ["date", "summary", "activities"]):
                    return parsed
            except:
                continue
    
    # Strategy 3: Find first { to last } and try to parse
    start = resp_text.find('{')
    end = resp_text.rfind('}') + 1
    
    if start != -1 and end > start:
        candidate = sanitize_to_json_str(resp_text[start:end])
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                # Force structure even if incomplete
                return {
                    "date": parsed.get("date", "unknown"),
                    "employee_id": parsed.get("employee_id", "unknown"),
                    "summary": parsed.get("summary", "Parse error - incomplete summary"),
                    "activities": parsed.get("activities", {}),
                    "insights": parsed.get("insights", [])
                }
        except:
            pass
    
    # Strategy 4: Emergency fallback - extract text content manually
    print(f"[parse_json_response] ⚠️ All parsing failed, using emergency extraction")
    
    # Try to salvage summary
    summary_match = re.search(r'"summary"\s*:\s*"([^"]+)"', resp_text)
    summary = summary_match.group(1) if summary_match else "Failed to extract summary"
    
    return {
        "summary": summary,
        "activities": {},
        "insights": ["Parsing failed - manual review needed"],
        "date": "unknown",
        "employee_id": "unknown"
    }
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
def smart_dynamic_batches(chunks: List[Dict[str, Any]], max_tokens=6000):
    chunks = sorted(chunks, key=lambda c: c.get("start_time", ""))  # Chronological only
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
"""def summarize_day_batch(chunks: List[Dict[str, Any]], employee_id: str, date_part: str,
                        previous_context: str = "", retries: int = 3) -> Dict[str, Any]:
    if not chunks:
        return {"employee_id": employee_id, "date": date_part, "summary": "", "activities": {}, "insights": []}
    filtered_chunks = []
    seen_summaries = set()
    prepared = []
    for c in chunks:
        text = clean_summary_text(c.get("summary_text", ""))
        if text in seen_summaries:
            continue
        if c.get("confidence", 0) < 0.4:
            continue
        if text.count("(x") > 5: 
            continue
        seen_summaries.add(text)
        filtered_chunks.append(c)
        if not filtered_chunks:
            return {"employee_id": employee_id, "date": date_part, "summary": "No significant activity", "activities": {}, "insights": []}
    
        chunks = filtered_chunks  # Use filtered version
    
        prepared = []

        duration = c.get("duration", None)
        duration_str = f"{duration} min" if duration is not None else "unknown"
        prepared.append(f"[{c.get('category', 'Unknown')}] {text} (Duration: {duration_str}; "
                        f"{c.get('start_time','?')} → {c.get('end_time','?')})")

    joined_text = "\n".join(prepared)
    if estimate_tokens(joined_text) > 3000:  # ~750 tokens max for logs
        # Keep first 40% and last 40%, skip middle
        split_point = len(prepared) // 2
        keep_first = int(len(prepared) * 0.4)
        keep_last = int(len(prepared) * 0.4)
        prepared = prepared[:keep_first] + ["... [middle activities truncated] ..."] + prepared[-keep_last:]
        joined_text = "\n".join(prepared)
    prev_ctx = previous_context[:4000] if previous_context else ""

    prompt = fAnalyze employee activity logs and return ONLY valid JSON.

Employee: {employee_id}
Date: {date_part}

Activity Logs:
{joined_text}

Previous Context: {prev_ctx}

Return this exact JSON structure:
{{
  "date": "{date_part}",
  "employee_id": "{employee_id}",
  "summary": "One sentence overview of what the employee accomplished",
  "activities": {{
    "CategoryName": ["specific action 1", "specific action 2"]
  }},
  "insights": ["insight about focus", "insight about efficiency", "insight about patterns"]
}}

Rules:
- Summary: Single sentence, factual, no fluff
- Activities: Group by category (Development, Cloud Operations, Meetings, etc.)
- Insights: 3 specific observations about work patterns
- Use ONLY categories that appear in the logs
- NO text outside the JSON object

    for attempt in range(retries):
        try:
            llm_start = time.time()
            #payload = {"model": OLLAMA_MODEL, "prompt": prompt, "options": {"temperature": 0.35}, "stream": False}
            #resp = requests.post(OLLAMA_URL, json=payload, timeout=360)
            # Define expected JSON schema
            json_schema = {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "employee_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "activities": {
                        "type": "object",
                        "additionalProperties": {"type": "array", "items": {"type": "string"}}
                    },
                    "insights": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["date", "employee_id", "summary", "activities", "insights"]
            }

            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",  # Force JSON mode
                "options": {"temperature": 0.35},
                "stream": False
            }

            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=360)
            resp.raise_for_status()
            llm_end = time.time()
            print(f"[summarize_day_batch] ⏱ LLM response received in {llm_end - llm_start:.2f} seconds")
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

"""
"""def summarize_day_batch(chunks: List[Dict[str, Any]], employee_id: str, date_part: str,
                        previous_context: str = "", retries: int = 3) -> Dict[str, Any]:
    if not chunks:
        return {"employee_id": employee_id, "date": date_part, "summary": "", "activities": {}, "insights": []}

    # Filter chunks
    filtered_chunks = []
    seen_summaries = set()
    for c in chunks:
        text = c.get("summary_text", "")
        if text in seen_summaries or c.get("confidence", 0) < 0.4:
            continue
        seen_summaries.add(text)
        filtered_chunks.append(c)
    
    if not filtered_chunks:
        return {"employee_id": employee_id, "date": date_part, "summary": "No significant activity", "activities": {}, "insights": []}
    
    chunks = filtered_chunks

    # Prepare text
    prepared = []
    for c in chunks:
        text = clean_summary_text(c.get("summary_text", ""))
        duration = c.get("duration", None)
        duration_str = f"{duration} min" if duration is not None else "unknown"
        prepared.append(f"[{c.get('category', 'Unknown')}] {text} (Duration: {duration_str})")

    # Smart truncation
    joined_text = "\n".join(prepared)
    if estimate_tokens(joined_text) > 2500:
        keep_first = int(len(prepared) * 0.4)
        keep_last = int(len(prepared) * 0.4)
        prepared = prepared[:keep_first] + ["... [middle activities omitted] ..."] + prepared[-keep_last:]
        joined_text = "\n".join(prepared)

    prev_ctx = previous_context[:2000] if previous_context else ""

    # Simplified prompt
    prompt = fAnalyze employee activity and return ONLY valid JSON.

Employee: {employee_id} | Date: {date_part}

Activity Logs:
{joined_text}

Previous Context: {prev_ctx}

Return this exact JSON structure:
{{
  "date": "{date_part}",
  "employee_id": "{employee_id}",
  "summary": "One factual sentence about what was accomplished",
  "activities": {{"Category": ["action1", "action2"]}},
  "insights": ["pattern observation 1", "efficiency note 2", "focus analysis 3"]
}}
Rules:
- Summary: Single sentence, factual, no fluff
- Activities: Group by category (Development, Cloud Operations, Meetings, etc.)
- Insights: 3 specific observations about work patterns
- Use ONLY categories that appear in the logs
- NO text outside the JSON object


    for attempt in range(retries):
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",  # FORCE JSON OUTPUT
                "options": {"temperature": 0.3},
                "stream": False
            }
            
            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=360)
            resp.raise_for_status()
            
            text = extract_text_from_response(resp.json()).strip()
            
            # Debug: save raw response
            with open(f"raw_batch_{employee_id}_{date_part}_attempt{attempt}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
            parsed = parse_json_response(text)
            
            # VALIDATE structure
            if not isinstance(parsed, dict):
                print(f"[Attempt {attempt+1}] ❌ Not a dict: {type(parsed)}")
                continue
            
            # Ensure required fields
            parsed.setdefault("date", date_part)
            parsed.setdefault("employee_id", employee_id)
            parsed.setdefault("summary", "No summary")
            parsed.setdefault("activities", {})
            parsed.setdefault("insights", [])
            
            # Clean activities
            cleaned_activities = {}
            for k, v in parsed["activities"].items():
                if isinstance(v, list):
                    cleaned_activities[k] = [str(i) for i in v if i]
                else:
                    cleaned_activities[k] = [str(v)]
            parsed["activities"] = cleaned_activities
            
            # Clean insights
            parsed["insights"] = [str(i) for i in parsed["insights"] if i][:10]
            
            if not parsed["insights"]:
                parsed["insights"] = ["Steady work pattern", "Moderate multitasking", "Focus maintained"]
            
            parsed["generated_at"] = datetime.utcnow().isoformat()
            
            print(f"[✅ Attempt {attempt+1}] Successfully parsed batch for {employee_id}")
            return parsed

        except Exception as e:
            print(f"[Attempt {attempt+1}/{retries}] ❌ Error: {e}")
            time.sleep(2)

    # Final fallback
    print("[❌ FALLBACK] All attempts failed, using deterministic summary")
    activities = {}
    for c in chunks:
        cat = c.get("category", "Unknown")
        activities.setdefault(cat, []).append(clean_summary_text(c.get("summary_text", ""))[:150])
    
    return {
        "employee_id": employee_id,
        "date": date_part,
        "summary": "Automatic fallback summary due to parsing failures",
        "activities": activities,
        "insights": ["Fallback mode - manual review recommended"],
        "generated_at": datetime.utcnow().isoformat(),
    }"""
def summarize_day_batch(chunks: List[Dict[str, Any]], employee_id: str, date_part: str,
                        previous_context: str = "", retries: int = 3) -> Dict[str, Any]:
    start_time = time.time()
    
    if not chunks:
        return {"employee_id": employee_id, "date": date_part, "summary": "", "activities": {}, "insights": []}

    # Filter chunks
    filtered_chunks = []
    seen_summaries = set()
    for c in chunks:
        text = c.get("summary_text", "")
        if text in seen_summaries or c.get("confidence", 0) < 0.4:
            continue
        seen_summaries.add(text)
        filtered_chunks.append(c)
    
    if not filtered_chunks:
        return {"employee_id": employee_id, "date": date_part, "summary": "No significant activity", "activities": {}, "insights": []}
    
    chunks = filtered_chunks

    # ✅ FIX 1: Prepare text with NORMALIZED categories
    prepared = []
    categories_present = set()  # Will store normalized versions
    category_display_map = {}   # Maps normalized -> original for display
    
    for c in chunks:
        text = clean_summary_text(c.get("summary_text", ""))
        duration = c.get("duration", None)
        duration_str = f"{duration:.1f} min" if duration is not None else "unknown"
        category = c.get("category", "Unknown")
        
        # Normalize category for matching
        category_normalized = category.strip().lower()
        categories_present.add(category_normalized)
        
        # Store first occurrence of original category name for display
        if category_normalized not in category_display_map:
            category_display_map[category_normalized] = category
        
        prepared.append(f"[{category}] {text} (Duration: {duration_str})")
    
    print(f"[DEBUG] Normalized categories in batch: {categories_present}")
    print(f"[DEBUG] Display names: {category_display_map}")

    # Smart truncation
    joined_text = "\n".join(prepared)
    if estimate_tokens(joined_text) > 4500:
        keep_first = int(len(prepared) * 0.4)
        keep_last = int(len(prepared) * 0.4)
        prepared = prepared[:keep_first] + ["... [middle activities omitted] ..."] + prepared[-keep_last:]
        joined_text = "\n".join(prepared)

    # Safely truncate context
    if previous_context and len(previous_context) > 2000:
        prev_ctx = previous_context[:2000].rsplit('.', 1)[0] + "..."
    else:
        prev_ctx = previous_context or ""
    
    # List categories for the LLM (use display names)
    categories_str = ", ".join(f'"{category_display_map[cat]}"' for cat in sorted(categories_present) if cat != "unknown")

    prompt = f"""You are an AI work analyst. Summarize the employee's work activities below.

Employee: {employee_id}
Date: {date_part}

Activity Logs (each line shows [Category] action):
{joined_text}

Previous batch context: {prev_ctx}

Categories present in this batch: {categories_str}

Your task:
1. Write ONE factual summary sentence about key accomplishments
2. Group specific actions by their category (use the categories listed above)
3. Extract SPECIFIC actions from the logs (mention actual files, tools, commands)
4. Provide 3 insights about work patterns (focus, efficiency, collaboration, etc.)

Critical rules:
- Use categories EXACTLY as shown above
- Extract real details: file names, applications, commands, URLs
- Do NOT invent actions not in the logs
- Do NOT copy example text
- Insights must be about THIS batch, not generic

Return ONLY this JSON structure:
{{
  "date": "{date_part}",
  "employee_id": "{employee_id}",
  "summary": "<factual sentence about this work session>",
  "activities": {{
    "<category from list>": ["<specific action from logs>", "<another action>"]
  }},
  "insights": ["<observation about focus>", "<observation about efficiency>", "<observation about patterns>"]
}}
Now analyze the logs above and return ONLY JSON (no markdown, no extra text):
"""

    retry_count = 0
    for attempt in range(retries):
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "format": "json",
                "options": {"temperature": 0.25},
                "stream": False
            }
            
            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=360)
            resp.raise_for_status()
            
            text = extract_text_from_response(resp.json()).strip()
            
            # Debug
            with open(f"raw_batch_{employee_id}_{date_part}_attempt{attempt}.txt", "w", encoding="utf-8") as f:
                f.write(text)
            
            parsed = parse_json_response(text)
            
            if not isinstance(parsed, dict):
                print(f"[Attempt {attempt+1}] ❌ Not a dict: {type(parsed)}")
                continue
            
            # Ensure required fields
            parsed.setdefault("date", date_part)
            parsed.setdefault("employee_id", employee_id)
            parsed.setdefault("summary", "No summary generated")
            parsed.setdefault("activities", {})
            parsed.setdefault("insights", [])
            
            # Check for template placeholders
            activities = parsed.get("activities", {})
            if "Category" in activities or "action1" in str(activities).lower() or "action2" in str(activities).lower():
                print(f"[Attempt {attempt+1}] ⚠️ LLM used template placeholders, retrying...")
                continue
            
            # ✅ FIX 2: Clean activities with NORMALIZED comparison
            cleaned_activities = {}
            
            for k, v in activities.items():
                # Normalize LLM's category for comparison
                k_normalized = k.strip().lower()
                
                print(f"[DEBUG] Validating category: '{k}' → normalized: '{k_normalized}'")
                print(f"[DEBUG] Valid categories: {categories_present}")
                print(f"[DEBUG] Is valid? {k_normalized in categories_present}")
                
                # Skip if category not in our normalized set
                if k_normalized not in categories_present and k_normalized != "unknown":
                    print(f"[Attempt {attempt+1}] ⚠️ Skipping invalid category: '{k}'")
                    continue
                
                # Process actions
                if isinstance(v, list):
                    real_actions = [
                        str(i) for i in v 
                        if i and 
                        "action1" not in str(i).lower() and 
                        "action2" not in str(i).lower() and
                        len(str(i).strip()) > 5
                    ]
                    if real_actions:
                        # Keep original category name from LLM (not normalized)
                        cleaned_activities[k] = real_actions
                else:
                    action_str = str(v)
                    if "action" not in action_str.lower() and len(action_str.strip()) > 5:
                        cleaned_activities[k] = [action_str]
            
            # If no activities survived cleaning, retry
            if not cleaned_activities:
                print(f"[Attempt {attempt+1}] ⚠️ No valid activities after cleaning, retrying...")
                continue
            
            parsed["activities"] = cleaned_activities
            
            # Clean insights (existing code)
            raw_insights = parsed.get("insights", [])
            good_insights = []
            bad_phrases = [
                "pattern observation", "efficiency note", "focus analysis",
                "employee spends", "various", "multiple tasks",
                "note 1", "note 2", "note 3",
                "observation 1", "observation 2"
            ]
            
            for insight in raw_insights:
                insight_str = str(insight).lower()
                if any(bad in insight_str for bad in bad_phrases) or len(insight) < 30:
                    continue
                good_insights.append(str(insight))
            
            if not good_insights:
                focus_time = sum(c.get("duration", 0) for c in chunks)
                app_switches = sum(1 for c in chunks if c.get("event") == "window_switch")
                good_insights = [
                    f"Sustained work period of {focus_time:.1f} minutes across {len(chunks)} activity segments",
                    f"Moderate context switching with {app_switches} application transitions",
                    f"Primary focus on {', '.join(category_display_map[cat] for cat in sorted(categories_present)[:2] if cat != 'unknown')} activities"
                ]
            
            parsed["insights"] = good_insights[:8]
            parsed["generated_at"] = datetime.utcnow().isoformat()
            
            print(f"[✅ Attempt {attempt+1}] Successfully parsed batch for {employee_id}")
            print(f"    └─ Categories: {', '.join(parsed['activities'].keys())}")
            print(f"    └─ Actions: {sum(len(v) for v in parsed['activities'].values())} total")
            
            elapsed = time.time() - start_time
            print(f"[Metrics] ⏱ summarize_day_batch took {elapsed:.2f}s, retries={retry_count}")
            return parsed

        except Exception as e:
            retry_count += 1
            print(f"[Attempt {attempt+1}/{retries}] ❌ Error: {e}")
            time.sleep(2)

    # Final fallback
    print("[❌ FALLBACK] All attempts failed, using deterministic summary")
    activities = {}
    for c in chunks:
        cat = c.get("category", "Unknown")
        text = clean_summary_text(c.get("summary_text", ""))
        if "typed:" in text or "Pasted" in text or "Switched to" in text:
            activities.setdefault(cat, []).append(text[:120])
    
    elapsed = time.time() - start_time
    print(f"[Metrics] ⏱ summarize_day_batch took {elapsed:.2f}s, retries={retry_count}")
    
    return {
        "employee_id": employee_id,
        "date": date_part,
        "summary": f"Work session covering {', '.join(category_display_map.get(cat, cat) for cat in categories_present if cat != 'unknown')}",
        "activities": activities,
        "insights": [
            f"Activity spanned {len(chunks)} segments across {len(categories_present)} categories",
            "Automated summary - detailed analysis unavailable",
            "Manual review recommended for accuracy"
        ],
        "generated_at": datetime.utcnow().isoformat(),
    }
# -------------------------
# Final refinement + Elasticsearch save (unchanged)
# -------------------------
"""def refine_final_summary(summary_data: Dict[str, Any]) -> Dict[str, Any]:
 
    # Validate input
    if not summary_data.get("summary") or not summary_data.get("activities"):
        print(f"[refine_final_summary] ⚠️ Insufficient data to refine, returning as-is")
        summary_data["generated_at"] = datetime.utcnow().isoformat()
        return summary_data
    
    input_text = json.dumps(summary_data, ensure_ascii=False)[:15000]  # Reduced from 20000
    
    prompt = f""""""Combine the following batch summaries into a single coherent daily report.

Employee: {summary_data.get('employee_id', 'unknown')}
Date: {summary_data.get('date', 'unknown')}

Batch Data:
{input_text}

Return this JSON structure (NO extra text):
{{
  "date": "{summary_data.get('date', 'unknown')}",
  "employee_id": "{summary_data.get('employee_id', 'unknown')}",
  "summary": "One comprehensive sentence about the entire day",
  "activities": {{"Category": ["chronological action 1", "action 2"]}},
  "insights": ["efficiency pattern", "focus analysis", "productivity note"]
}}

Rules:
- Chronological order for activities
- Remove redundant/repetitive actions
- Keep top 3-5 most important insights
- Summary should capture overall productivity, not details
""""""

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",  # ✅ FORCE JSON MODE
            "options": {"temperature": 0.25},  # Lower temp for refinement
            "stream": False
        }
        
        resp = requests.post(OLLAMA_URL, json=payload, timeout=360)
        resp.raise_for_status()
        
        text = extract_text_from_response(resp.json())
        
        # Debug
        with open(f"raw_refine_{summary_data.get('employee_id')}_{summary_data.get('date')}.txt", "w", encoding="utf-8") as f:
            f.write(text)
        
        parsed = parse_json_response(text)
        
        # VALIDATE required fields
        if not isinstance(parsed, dict):
            raise ValueError("Parsed result is not a dict")
        
        # Ensure structure
        parsed.setdefault("date", summary_data.get("date"))
        parsed.setdefault("employee_id", summary_data.get("employee_id"))
        parsed.setdefault("summary", summary_data.get("summary"))
        parsed.setdefault("activities", summary_data.get("activities", {}))
        parsed.setdefault("insights", summary_data.get("insights", []))
        
        # Clean activities
        cleaned_activities = {}
        for k, v in parsed.get("activities", {}).items():
            if isinstance(v, list):
                cleaned_activities[k] = [str(i) for i in v if i]
            else:
                cleaned_activities[k] = [str(v)]
        parsed["activities"] = cleaned_activities
        
        # Limit insights
        parsed["insights"] = [str(i) for i in parsed.get("insights", []) if i][:8]
        
        parsed["generated_at"] = datetime.utcnow().isoformat()
        
        print(f"[refine_final_summary] ✅ Successfully refined summary")
        return parsed
        
    except Exception as e:
        print(f"[refine_final_summary] ❌ Error: {e}, returning unrefined summary")
        summary_data["generated_at"] = datetime.utcnow().isoformat()
        return summary_data
"""

def refine_final_summary(summary_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refine multiple batch summaries into a coherent daily report.
    """
    refine_start = time.time()  # ADD at top

    # Validate input
    if not summary_data.get("summary") or not summary_data.get("activities"):
        print(f"[refine_final_summary] ⚠️ Insufficient data to refine, returning as-is")
        summary_data["generated_at"] = datetime.utcnow().isoformat()
        return summary_data
    
    # Extract categories from activities
    categories_present = list(summary_data.get("activities", {}).keys())
    categories_str = ", ".join(f'"{cat}"' for cat in categories_present)
    
    # Prepare batch summaries for context
    batch_summaries = []
    for cat, actions in summary_data.get("activities", {}).items():
        if actions:
            batch_summaries.append(f"[{cat}]: {len(actions)} actions")
    
    input_text = json.dumps(summary_data, ensure_ascii=False)[:12000]
    
    prompt = f"""You are an AI work analyst. You have multiple batch summaries from throughout the day. Combine them into ONE coherent daily summary.

Employee: {summary_data.get('employee_id')}
Date: {summary_data.get('date')}

Categories : {categories_str}

Batch Summaries Data:
{input_text}

Your task:
1. Write ONE comprehensive summary for the entire day
2. Merge activities by category (chronologically)
3. Deduplicate similar actions
4. Keep 3-5 most important insights

Rules:
- Use ONLY categories from the list above
- Extract real details from batch data, don't invent
- Remove duplicate actions
- Insights should reflect FULL day

Return ONLY JSON:
{{
  "date": "{summary_data.get('date')}",
  "employee_id": "{summary_data.get('employee_id')}",
  "summary": "<daily summary>",
  "activities": {{"<category>": ["<action1>", "<action2>"]}},
  "insights": ["<daily insight 1>", "<daily insight 2>", "<daily insight 3>"]
}}

"""

    try:
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "options": {"temperature": 0.2},  # Even lower for refinement
            "stream": False
        }
        
        resp = requests.post(OLLAMA_URL, json=payload, timeout=360)
        resp.raise_for_status()
        
        text = extract_text_from_response(resp.json())
        
        # Debug
        with open(f"raw_refine_{summary_data.get('employee_id')}_{summary_data.get('date')}.txt", "w", encoding="utf-8") as f:
            f.write(text)
        
        parsed = parse_json_response(text)
        
        # VALIDATE required fields
        if not isinstance(parsed, dict):
            raise ValueError("Parsed result is not a dict")
        
        # Ensure structure
        parsed.setdefault("date", summary_data.get("date"))
        parsed.setdefault("employee_id", summary_data.get("employee_id"))
        parsed.setdefault("summary", summary_data.get("summary"))
        parsed.setdefault("activities", summary_data.get("activities", {}))
        parsed.setdefault("insights", summary_data.get("insights", []))
        
        # CRITICAL: Validate no example text leaked through
        activities = parsed.get("activities", {})
        # Check for generic placeholder patterns instead
        example_patterns = [
            r"file\d+\.py",  # file1.py, file2.py
            r"action\d+",    # action1, action2
            r"<[^>]+>",      # <placeholder>
            r"\[.*\]"        # [description]
        ]        
        for cat, actions in activities.items():
            # Check if any example phrases appear
            actions_str = " ".join(str(a) for a in actions).lower()
            if any(phrase.lower() in actions_str for phrase in example_patterns):
                print(f"[refine_final_summary] ⚠️ Detected example text in activities, using unrefined summary")
                summary_data["generated_at"] = datetime.utcnow().isoformat()
                return summary_data
        
        # Clean activities - only keep valid categories
        cleaned_activities = {}
        for k, v in activities.items():
            if k not in categories_present:
                print(f"[refine_final_summary] ⚠️ Skipping invalid category: {k}")
                continue
            if isinstance(v, list):
                cleaned_activities[k] = [str(i) for i in v if i and len(str(i).strip()) > 5]
            else:
                cleaned_activities[k] = [str(v)]
        
        # If refinement removed too much, keep original
        if not cleaned_activities:
            print(f"[refine_final_summary] ⚠️ Refinement removed all activities, using unrefined")
            summary_data["generated_at"] = datetime.utcnow().isoformat()
            return summary_data
        
        parsed["activities"] = cleaned_activities
        
        # Clean insights - check for example text
        raw_insights = parsed.get("insights", [])
        example_insight_phrases = ["2.5 hours", "development → testing → deployment", "tests alongside feature"]
        
        good_insights = []
        for insight in raw_insights:
            insight_str = str(insight).lower()
            # Skip if contains example phrases
            if any(phrase.lower() in insight_str for phrase in example_insight_phrases):
                print(f"[refine_final_summary] ⚠️ Skipping example insight: {insight[:50]}...")
                continue
            if len(insight) > 20:
                good_insights.append(str(insight))
        
        # If all insights were examples, use originals
        if not good_insights:
            good_insights = summary_data.get("insights", [])[:5]
        
        parsed["insights"] = good_insights[:8]
        parsed["generated_at"] = datetime.utcnow().isoformat()
        
        print(f"[refine_final_summary] ✅ Successfully refined summary")
        print(f"    └─ Categories: {', '.join(parsed['activities'].keys())}")
        print(f"    └─ Total actions: {sum(len(v) for v in parsed['activities'].values())}")
        print(f"    └─ Insights: {len(parsed['insights'])}")
        elapsed = time.time() - refine_start
        print(f"[Metrics] ⏱ refine_final_summary took {elapsed:.2f}s")
        return parsed
        
    except Exception as e:
        print(f"[refine_final_summary] ❌ Error: {e}, returning unrefined summary")
        summary_data["generated_at"] = datetime.utcnow().isoformat()
        elapsed = time.time() - refine_start
        print(f"[Metrics] ❌ refine_final_summary failed in {elapsed:.2f}s")
        return summary_data
def summarize_and_store(chunks: List[Dict[str, Any]], employee_id: str, date: str):

    # STEP 1: Filter low-quality chunks FIRST
    original_count = len(chunks)
    chunks = [
        c for c in chunks 
        if c.get("confidence", 0) >= 0.4 
        and c.get("category", "Unknown") != "Unknown"
    ]
    filtered_count = len(chunks)
    
    if filtered_count < original_count:
        print(f"[summarize_and_store] 🗑️ Filtered out {original_count - filtered_count} low-quality chunks "
              f"({filtered_count}/{original_count} remaining)")
    
    # STEP 2: Check if we have enough data
    if not chunks:
        print(f"[summarize_and_store] ⚠️ No high-confidence chunks to summarize for {employee_id} on {date}")
        fallback_summary = {
            "employee_id": employee_id,
            "date": date,
            "summary": "Insufficient high-quality activity data for this day.",
            "activities": {},
            "insights": ["Data quality too low for meaningful analysis"],
            "generated_at": datetime.utcnow().isoformat()
        }
        save_summary_to_es(fallback_summary)
        return fallback_summary
    
    # STEP 3: Create batches from filtered chunks
    batches = smart_dynamic_batches(chunks, max_tokens=4000)
    total_batches = len(batches)
    print(f"[summarize_and_store] 🧩 Created {total_batches} batch(es) for {employee_id} on {date}")
    print(f"[summarize_and_store] 📊 Batch sizes: {[len(b) for b in batches]}")
    
    # STEP 4: Summarize each batch
    batch_summaries = []
    rolling_context = ""
    
    for i, batch in enumerate(batches, 1):
        start_time = time.time()
        print(f"[summarize_and_store] 🚀 Starting batch {i}/{total_batches} "
              f"(size: {len(batch)} chunks) for {employee_id} on {date}")
        
        result = summarize_day_batch(
            batch, 
            employee_id, 
            f"{date}-part{i}", 
            previous_context=rolling_context
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"[summarize_and_store] ⏱ Batch {i} completed in {elapsed:.2f} seconds")
        
        batch_summaries.append(result)
        
        # Update rolling context for next batch
        short_ctx = {
            "summary": result.get("summary", ""), 
            "insights": result.get("insights", [])[:3]
        }
        rolling_context = json.dumps(short_ctx, ensure_ascii=False)[:3000]
        
        time.sleep(1)  # Rate limiting

    # STEP 5: Combine all batch summaries
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

    # STEP 6: Refine if multiple batches (optional but recommended)
    if total_batches > 1:
        print(f"[summarize_and_store] 🔄 Refining combined summary for {employee_id} on {date}...")
        combined = refine_final_summary(combined)
    
    # STEP 7: Validate before saving
    if combined.get("date") == "unknown" or combined.get("employee_id") == "unknown":
        print(f"[summarize_and_store] ⚠️ Refinement failed, using unrefined combined summary")
        combined["employee_id"] = employee_id
        combined["date"] = date

    # STEP 8: Save to Elasticsearch
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
