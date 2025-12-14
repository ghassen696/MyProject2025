from sentence_transformers import SentenceTransformer, util
import requests
import json
from typing import List, Dict

OLLAMA_MODEL = "llama3.2:latest"
MODEL = SentenceTransformer("all-MiniLM-L6-v2")  # lightweight & fast

# ---------------------------------------------------
# Precompute employee embeddings
# ---------------------------------------------------
def build_employee_embeddings(employee_histories: List[Dict]) -> List[Dict]:
    """
    Input: list of employee histories (each with 'employee_id', 'summary', 'insights')
    Output: list of dicts with embeddings
    """
    embeddings = []
    for emp in employee_histories:
        text_repr = f"{emp.get('summary','')}. Insights: {', '.join(emp.get('insights', []))}"
        vector = MODEL.encode(text_repr, convert_to_numpy=True)
        embeddings.append({
            "employee_id": emp["employee_id"],
            "vector": vector,
            "summary": emp.get("summary",""),
            "insights": emp.get("insights", [])
        })
    return embeddings

# ---------------------------------------------------
# Match a single task against precomputed embeddings
# ---------------------------------------------------
def match_task_live(task_description: str, employee_embeddings: List[Dict], top_k: int = 5) -> List[Dict]:
    task_vector = MODEL.encode(task_description, convert_to_numpy=True)
    results = []
    for emp in employee_embeddings:
        sim = float(util.cos_sim(task_vector, emp["vector"]))
        results.append({
            "employee_id": emp["employee_id"],
            "similarity": round(sim, 4),
            "summary": emp["summary"],
            "insights": emp["insights"]
        })
    results = sorted(results, key=lambda x: x["similarity"], reverse=True)[:top_k]
    return results

# ---------------------------------------------------
# Generate reasoning for top matches (optional)
# ---------------------------------------------------
def generate_reasoning_live(task_description: str, top_matches: List[Dict]) -> List[Dict]:
    reasoning_results = []
    for emp in top_matches:
        prompt = f"""
You are a senior productivity analyst. Evaluate the following task and employee history.
Provide a concise reasoning explaining why this employee is suitable (or not) for the task.

Task:
{task_description}

Employee Summary:
{emp.get('summary','')}

Employee Insights:
{', '.join(emp.get('insights', []))}

Return JSON:
{{"justification": "Explain why this employee matches this task in 1-2 sentences."}}
        """
        try:
            resp = requests.post(
                "http://193.95.30.190:11434/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "options":{"temperature":0.3}, "stream":False},
                timeout=120
            )
            resp.raise_for_status()
            result = json.loads(resp.json().get("response","").strip())
            reasoning_results.append({
                "employee_id": emp["employee_id"],
                "similarity": emp["similarity"],
                "justification": result.get("justification","")
            })
        except Exception as e:
            reasoning_results.append({
                "employee_id": emp["employee_id"],
                "similarity": emp["similarity"],
                "justification": "LLM failed to generate reasoning."
            })
    return reasoning_results

# ---------------------------------------------------
# High-level function: get suggestions + reasoning
# ---------------------------------------------------
def suggest_employees(tasks: List[Dict], employee_histories: List[Dict], top_k:int=3, reasoning:bool=True):
    # Precompute once
    employee_embeddings = build_employee_embeddings(employee_histories)
    
    all_suggestions = {}
    for t in tasks:
        task_desc = t["description"]
        matches = match_task_live(task_desc, employee_embeddings, top_k=top_k)
        if reasoning:
            matches_with_reasoning = generate_reasoning_live(task_desc, matches)
            all_suggestions[t["task_id"]] = matches_with_reasoning
        else:
            all_suggestions[t["task_id"]] = matches
    return all_suggestions

# ---------------------------------------------------
# Example usage
# ---------------------------------------------------
if __name__ == "__main__":
    # Example employee histories
    employee_histories = [
        {"employee_id":"E1","summary":"Developed backend APIs","insights":["Focus on performance","Debugged Elasticsearch queries"]},
        {"employee_id":"E2","summary":"Frontend dashboard design","insights":["Used React and Tailwind","Implemented charts"]},
        {"employee_id":"E3","summary":"Data analysis and reporting","insights":["Created daily summaries","Improved prediction accuracy"]}
    ]
    
    # Example tasks
    tasks = [
        {"task_id":"T1","description":"Optimize backend API and Elasticsearch queries"},
        {"task_id":"T2","description":"Design frontend dashboard to visualize daily summaries"}
    ]
    
    suggestions = suggest_employees(tasks, employee_histories, top_k=2, reasoning=True)
    
    for task_id, recs in suggestions.items():
        print(f"\n🔹 Task {task_id} Recommendations:")
        for r in recs:
            print(f"- {r['employee_id']} ({r['similarity']:.3f}): {r['justification']}")
