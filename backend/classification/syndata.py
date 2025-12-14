"""import random
from datetime import datetime, timedelta
import uuid
import json

# ----------------------
# Configuration
# ----------------------
TEAM = [
    {"employee_id": f"E{i+1}", "productivity": p} 
    for i, p in enumerate(["high", "medium", "low", "medium", "high", "low"])
]

WORK_START_HOUR = 9
WORK_END_HOUR = 18
LUNCH_START_HOUR = 12
LUNCH_END_HOUR = 13
START_DATE = datetime.strptime("2025-10-18", "%Y-%m-%d")
NUM_DAYS = 5  # Monday to Friday

EVENT_TYPES = ["keystroke", "shortcut", "window_switch", "clipboard_paste", "idle_start", "idle_end"]
SHORTCUTS = ["Ctrl+C", "Ctrl+V", "Alt+Tab", "Ctrl+S"]
WINDOWS = ["IDE", "Browser", "Terminal", "Email", "Docs"]
MEETING_WINDOWS = ["Teams Meeting", "Zoom Meeting"]

PRODUCTIVITY_PROFILE = {"high": 120, "medium": 70, "low": 40}  # events/hour

PAUSE_DURATION_LIMITS = {
    "Lunch": 60,
    "Bathroom": 15,
    "Phone_call": 10,
    "Meeting": 120,
    "Personal_break": 15
}
PAUSE_REASONS = list(PAUSE_DURATION_LIMITS.keys())

# Idle configuration per productivity
IDLE_FREQ = {"high": 0.01, "medium": 0.03, "low": 0.07}  # probability per event to trigger idle
IDLE_DURATION_SEC = {"high": (60, 180), "medium": (120, 300), "low": (180, 600)}

# ----------------------
# Helper functions
# ----------------------
def generate_event(employee, timestamp, seq_num):
    event_type = random.choices(
        ["keystroke", "shortcut", "window_switch", "clipboard_paste"],
        weights=[50, 5, 10, 10],
        k=1
    )[0]

    window = random.choice(WINDOWS)
    text = ""
    if event_type == "keystroke":
        text = random.choice(["import json", "print('Hello')", "df.head()", "SELECT * FROM table"])
    elif event_type == "shortcut":
        text = random.choice(SHORTCUTS)
    elif event_type == "clipboard_paste":
        text = random.choice(["employee_daily_report", "config.yaml", "data.csv"])
    elif event_type == "window_switch":
        window = random.choice(MEETING_WINDOWS)
        text = "Meeting"
    return {
        "timestamp": timestamp.isoformat(),
        "event": event_type,
        "window": window,
        "application": window.split()[0],
        "control": "",
        "text": text,
        "employee_id": employee["employee_id"],
        "session_id": str(uuid.uuid4()),
        "seq_num": seq_num
    }

def generate_pause(employee, timestamp, reason, seq_num):
    duration = PAUSE_DURATION_LIMITS[reason]
    return [
        {
            "timestamp": timestamp.isoformat(),
            "event": "pause",
            "reason": reason,
            "duration_minutes": duration,
            "employee_id": employee["employee_id"],
            "session_id": str(uuid.uuid4()),
            "seq_num": seq_num
        }
    ]

def generate_idle(employee, timestamp, seq_num_start):
    min_sec, max_sec = IDLE_DURATION_SEC[employee["productivity"]]
    duration_sec = random.randint(min_sec, max_sec)
    idle_id = str(uuid.uuid4())
    return [
        {
            "timestamp": timestamp.isoformat(),
            "event": "idle_start",
            "window": "",
            "application": "",
            "control": "",
            "text": "",
            "employee_id": employee["employee_id"],
            "session_id": str(uuid.uuid4()),
            "seq_num": seq_num_start,
            "idle_id": idle_id,
            "idle_duration_sec": None
        },
        {
            "timestamp": (timestamp + timedelta(seconds=duration_sec)).isoformat(),
            "event": "idle_end",
            "window": "",
            "application": "",
            "control": "",
            "text": "",
            "employee_id": employee["employee_id"],
            "session_id": str(uuid.uuid4()),
            "seq_num": seq_num_start+1,
            "idle_id": idle_id,
            "idle_duration_sec": duration_sec
        }
    ]

# ----------------------
# Generate synthetic week
# ----------------------
all_events = []
seq_counters = {emp["employee_id"]: 1 for emp in TEAM}  # continuous seq_num

for day_offset in range(NUM_DAYS):
    current_date = START_DATE + timedelta(days=day_offset)
    work_start = current_date.replace(hour=WORK_START_HOUR, minute=0, second=0)
    work_end = current_date.replace(hour=WORK_END_HOUR, minute=0, second=0)
    lunch_time = current_date.replace(hour=LUNCH_START_HOUR, minute=0, second=0)

    for employee in TEAM:
        current_time = work_start
        seq_num = seq_counters[employee["employee_id"]]

        # Mandatory lunch
        all_events.extend(generate_pause(employee, lunch_time, "Lunch", seq_num))
        seq_num += 2

        # Random pauses (other than lunch)
        num_pauses = random.randint(1, 3)
        pause_times = sorted(random.sample(range((WORK_END_HOUR-WORK_START_HOUR)*60), num_pauses))
        for pt in pause_times:
            pause_reason = random.choice([r for r in PAUSE_REASONS if r != "Lunch"])
            pause_timestamp = work_start + timedelta(minutes=pt)
            all_events.extend(generate_pause(employee, pause_timestamp, pause_reason, seq_num))
            seq_num += 1

        # Generate events
        while current_time < work_end:
            # Skip lunch period
            if lunch_time <= current_time < lunch_time + timedelta(minutes=PAUSE_DURATION_LIMITS["Lunch"]):
                current_time = lunch_time + timedelta(minutes=PAUSE_DURATION_LIMITS["Lunch"])
                continue

            events_per_hour = PRODUCTIVITY_PROFILE[employee["productivity"]]
            avg_interval_sec = 3600 // events_per_hour
            timestamp = current_time + timedelta(seconds=random.randint(0, avg_interval_sec))

            # Insert idle based on productivity
            if random.random() < IDLE_FREQ[employee["productivity"]]:
                idle_events = generate_idle(employee, timestamp, seq_num)
                all_events.extend(idle_events)
                seq_num += 2
                timestamp += timedelta(seconds=(idle_events[1]["idle_duration_sec"]))

            event = generate_event(employee, timestamp, seq_num)
            all_events.append(event)
            seq_num += 1
            current_time += timedelta(seconds=avg_interval_sec)

        seq_counters[employee["employee_id"]] = seq_num

# Sort by employee and seq
all_events.sort(key=lambda x: (x['employee_id'], x['seq_num']))

# Save JSON
with open("synthetic_team_week_idle_realistic.json", "w") as f:
    json.dump(all_events, f, indent=2)

print(f"Generated {len(all_events)} events for {len(TEAM)} employees over {NUM_DAYS} days.")
"""
import re
from typing import List, Dict, Tuple
from elasticsearch import Elasticsearch
from collections import defaultdict

ES = Elasticsearch("http://193.95.30.190:9200")
KPI_INDEX = "employee_kpi_summary4"

def extract_skills_from_kpi(employee_id: str, date: str) -> List[Dict[str, any]]:
    """
    Extract skills with confidence scores based on:
    1. Time spent in relevant windows (70% weight)
    2. Category distribution from donut chart (20% weight)
    3. Active applications (10% weight)
    
    Returns: List of dicts with {skill, confidence, evidence}
    """
    doc_id = f"{employee_id}-{date}"
    
    # ========== SKILL MAPPINGS ==========
    
    APP_SKILLS = {
        "code.exe": ["VS Code", "Development", "Coding"],
        "cursor.exe": ["AI-Assisted Coding", "Development"],
        "chrome.exe": ["Web Research"],
        "msedge.exe": ["Web Research"],
        "windowsterminal.exe": ["CLI", "Terminal", "DevOps"],
        "cmd.exe": ["CLI", "Command Line"],
        "powershell.exe": ["PowerShell", "Scripting"],
        "pycharm64.exe": ["Python", "IDE", "Development"],
        "idea64.exe": ["Java", "IDE", "Development"],
        "postman.exe": ["API Testing", "REST"],
        "docker": ["Docker", "Containerization", "DevOps"],
        "kubectl": ["Kubernetes", "Orchestration"],
    }
    
    WINDOW_PATTERNS = {
        # Programming Languages
        r"\bpython\b|\.py\b": ["Python", "Backend"],
        r"\bjava\b|\.java\b": ["Java", "Backend"],
        r"\bjavascript\b|\.js\b": ["JavaScript"],
        r"\btypescript\b|\.ts\b|\.tsx\b": ["TypeScript"],
        r"\breact\b|\.jsx\b": ["React", "Frontend"],
        r"\bvue\b|\.vue\b": ["Vue.js", "Frontend"],
        r"\bangular\b": ["Angular", "Frontend"],
        r"\bnode\.js\b|\bnode\b": ["Node.js", "Backend"],
        r"\bc\+\+\b|\.cpp\b": ["C++"],
        r"\bc#\b|\.cs\b": ["C#", ".NET"],
        r"\bgo\b|golang\b|\.go\b": ["Go"],
        r"\bphp\b|\.php\b": ["PHP"],
        
        # Frameworks
        r"\bfastapi\b": ["FastAPI", "Python", "REST API"],
        r"\bdjango\b": ["Django", "Python"],
        r"\bflask\b": ["Flask", "Python"],
        r"\bspring\b": ["Spring", "Java"],
        r"\bexpress\b": ["Express.js", "Node.js"],
        r"\bnext\.js\b": ["Next.js", "React"],
        r"\btailwind\b": ["Tailwind CSS", "CSS"],
        
        # Databases
        r"\bmongodb\b|mongo\b": ["MongoDB", "NoSQL", "Database"],
        r"\bpostgresql\b|postgres\b": ["PostgreSQL", "SQL"],
        r"\bmysql\b": ["MySQL", "SQL"],
        r"\bredis\b": ["Redis", "Cache"],
        r"\belasticsearch\b": ["Elasticsearch", "Search Engine"],
        r"\bsqlite\b": ["SQLite", "SQL"],
        
        # DevOps & Cloud
        r"\bdocker\b": ["Docker", "Containerization"],
        r"\bkubernetes\b|k8s\b": ["Kubernetes", "Orchestration"],
        r"\baws\b": ["AWS", "Cloud"],
        r"\bazure\b": ["Azure", "Cloud"],
        r"\bgcp\b|google cloud": ["GCP", "Cloud"],
        r"\bterraform\b": ["Terraform", "IaC"],
        r"\bjenkins\b": ["Jenkins", "CI/CD"],
        r"\bgitlab\b": ["GitLab", "CI/CD"],
        r"\bgithub\b": ["GitHub", "Git"],
        
        # Data Science
        r"\bpandas\b": ["Pandas", "Data Analysis"],
        r"\bnumpy\b": ["NumPy", "Data Science"],
        r"\bscikit-learn\b|sklearn\b": ["Scikit-learn", "ML"],
        r"\btensorflow\b": ["TensorFlow", "Deep Learning"],
        r"\bpytorch\b": ["PyTorch", "Deep Learning"],
        r"\bjupyter\b": ["Jupyter", "Data Science"],
        
        # Web Tech
        r"\bhtml\b|\.html\b": ["HTML"],
        r"\bcss\b|\.css\b": ["CSS"],
        r"\bsass\b|\.scss\b": ["SASS"],
        r"\bgraphql\b": ["GraphQL", "API"],
        r"\brest api\b": ["REST API"],
        
        # Testing
        r"\bpytest\b": ["Pytest", "Testing"],
        r"\bjest\b": ["Jest", "Testing"],
        r"\bselenium\b": ["Selenium", "Testing"],
        
        # Tools
        r"\bstackoverflow\b": ["Problem Solving", "Research"],
        r"\bgithub\b": ["Open Source"],
        r"\bjira\b": ["Agile", "Project Management"],
        r"\bfigma\b": ["UI/UX", "Design"],
        r"\bconfluence\b": ["Documentation"],
        r"\blucidchart\b": ["Diagramming", "Documentation"],
        r"\bgoogle chrome\b": ["Web Research"],
        r"\bvisual studio code\b|vs code\b": ["VS Code", "Development"],
    }
    
    CATEGORY_SKILLS = {
        "Coding": ["Development", "Programming"],
        "Documentation": ["Technical Writing", "Documentation"],
        "Research": ["Research", "Learning"],
        "Browsing": ["Web Research"],
        "Communication": ["Collaboration", "Communication"],
        "Meetings": ["Collaboration", "Communication"],
        "Design": ["Design", "Creative"],
    }
    
    try:
        kpi_doc = ES.get(index=KPI_INDEX, id=doc_id)
        src = kpi_doc["_source"]
        
        # Store skills with time-based confidence
        skill_scores: Dict[str, Dict] = defaultdict(lambda: {
            "time_minutes": 0.0,
            "sources": [],
            "category_boost": 0.0,
            "app_boost": 0.0
        })
        
        total_active_time = src.get("active_min", 0)
        if total_active_time == 0:
            return []
        
        # ========== 1. EXTRACT FROM WINDOWS (70% weight) ==========
        time_per_window = src.get("time_per_window", [])
        
        # Focus on top windows by time (most impactful)
        sorted_windows = sorted(
            [w for w in time_per_window if isinstance(w, dict) and "window" in w],
            key=lambda x: x.get("time_spent_min", 0),
            reverse=True
        )
        
        # Process top 10 windows (or all if fewer)
        for window_entry in sorted_windows[:10]:
            window_title = window_entry.get("window", "")
            time_spent = window_entry.get("time_spent_min", 0)
            
            if time_spent < 0.5:  # Ignore very short interactions
                continue
            
            window_lower = window_title.lower()
            
            # Match patterns
            for pattern, skills in WINDOW_PATTERNS.items():
                if re.search(pattern, window_lower, re.IGNORECASE):
                    for skill in skills:
                        skill_scores[skill]["time_minutes"] += time_spent
                        skill_scores[skill]["sources"].append(
                            f"Window: {window_title[:50]}... ({time_spent:.1f}m)"
                        )
        
        # ========== 2. CATEGORY DISTRIBUTION (20% weight) ==========
        donut_data = src.get("donut_chart", [])
        for entry in donut_data:
            category = entry.get("category", "")
            minutes = entry.get("minutes", 0)
            
            if category in CATEGORY_SKILLS:
                for skill in CATEGORY_SKILLS[category]:
                    skill_scores[skill]["category_boost"] += minutes
                    if category not in [s.split(":")[0] for s in skill_scores[skill]["sources"]]:
                        skill_scores[skill]["sources"].append(
                            f"Category: {category} ({minutes:.0f}m)"
                        )
        
        # ========== 3. ACTIVE APPLICATIONS (10% weight) ==========
        active_apps = src.get("active_per_app", [])
        for app_entry in active_apps:
            app_name = app_entry.get("application", "").lower()
            keystroke_count = app_entry.get("keystroke_count", 0)
            
            for app_key, skills in APP_SKILLS.items():
                if app_key in app_name:
                    for skill in skills:
                        skill_scores[skill]["app_boost"] += keystroke_count / 100
                        if f"App: {app_name}" not in skill_scores[skill]["sources"]:
                            skill_scores[skill]["sources"].append(f"App: {app_name}")
        
        # ========== 4. CALCULATE FINAL CONFIDENCE SCORES ==========
        final_skills = []
        
        for skill, data in skill_scores.items():
            # Weighted score calculation
            time_score = (data["time_minutes"] / total_active_time) * 0.7
            category_score = (data["category_boost"] / total_active_time) * 0.2
            app_score = min(data["app_boost"] / 10, 0.1)  # Cap at 10%
            
            confidence = time_score + category_score + app_score
            
            # Only include skills with meaningful confidence (>2%)
            if confidence >= 0.02:
                final_skills.append({
                    "skill": skill,
                    "confidence": round(confidence, 4),
                    "time_minutes": round(data["time_minutes"], 1),
                    "evidence": data["sources"][:3]  # Top 3 sources
                })
        
        # ========== 5. POST-PROCESSING ==========
        # Sort by confidence
        final_skills.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Remove redundant generic skills if specific ones exist
        skill_names = [s["skill"] for s in final_skills]
        
        if any(lang in skill_names for lang in ["Python", "Java", "JavaScript"]):
            final_skills = [s for s in final_skills if s["skill"] not in ["Development", "Coding", "Programming"]]
        
        if any(fw in skill_names for fw in ["FastAPI", "Django", "Flask"]):
            final_skills = [s for s in final_skills if s["skill"] != "Backend"]
        
        # Return top 15 skills
        return final_skills[:15]
        
    except Exception as e:
        print(f"⚠️ Could not extract skills for {employee_id} on {date}: {e}")
        return []


def get_skill_names_only(employee_id: str, date: str, min_confidence: float = 0.03) -> List[str]:
    """
    Convenience function to get just skill names above confidence threshold
    For backward compatibility with existing code
    """
    skills_with_scores = extract_skills_from_kpi(employee_id, date)
    return [
        s["skill"] 
        for s in skills_with_scores 
        if s["confidence"] >= min_confidence
    ]


# ========== USAGE EXAMPLES ==========
if __name__ == "__main__":
    # Full detailed output
    print("=== DETAILED SKILLS WITH CONFIDENCE ===")
    skills = extract_skills_from_kpi("G50047910-5JjP5", "2025-11-23")
    
    for skill_data in skills:
        print(f"\n{skill_data['skill']}: {skill_data['confidence']:.1%} confidence")
        print(f"  Time spent: {skill_data['time_minutes']:.1f} minutes")
        print(f"  Evidence: {', '.join(skill_data['evidence'][:2])}")
    
    print("\n\n=== SIMPLE SKILL LIST (>3% confidence) ===")
    simple_skills = get_skill_names_only("G50047910-5JjP5", "2025-11-23", min_confidence=0.03)
    print(simple_skills)