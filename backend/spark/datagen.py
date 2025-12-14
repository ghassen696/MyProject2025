import json
import random
import uuid
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch

# Connect to Elasticsearch
es = Elasticsearch(['http://193.95.30.190:9200'])

# Employee profiles with different performance levels
EMPLOYEES = {
    "EMP001-CloudArchitect": {
        "name": "Ghassen Gagui",
        "role": "Senior Cloud Architect",
        "level": "excellent",
        "team": "Cloud Infrastructure"
    },
    "EMP002-DevOpsLead": {
        "name": "Ines Hammami",
        "role": "DevOps Team Lead",
        "level": "good",
        "team": "Cloud Infrastructure"
    },
    "EMP003-CloudEngineer": {
        "name": "Ghailene Gagui",
        "role": "Cloud Engineer",
        "level": "good",
        "team": "Cloud Infrastructure"
    },
    "EMP004-JuniorDev": {
        "name": "Hajer Ben Mahmoud",
        "role": "Junior Cloud Developer",
        "level": "moderate",
        "team": "Cloud Infrastructure"
    },
    "EMP005-Intern": {
        "name": "Amir Gamaoun",
        "role": "Cloud Engineering Intern",
        "level": "weak",
        "team": "Cloud Infrastructure"
    }
}

# Performance profiles for KPI generation
PERFORMANCE_PROFILES = {
    "excellent": {
        "work_hours": (8, 10),
        "productivity_score": (75, 95),
        "active_pct": (75, 90),
        "idle_pct": (5, 15),
        "pause_pct": (5, 10),
        "typing_chars": (15000, 25000),
        "focus_ratio": (0.7, 0.9),
        "context_switch_rate": (20, 35),
        "shortcuts_per_hour": (50, 80),
        "unique_apps": (8, 12),
        "coding_pct": (30, 45),
        "browsing_pct": (20, 30),
        "documentation_pct": (15, 25)
    },
    "good": {
        "work_hours": (7, 9),
        "productivity_score": (55, 75),
        "active_pct": (60, 75),
        "idle_pct": (15, 25),
        "pause_pct": (10, 15),
        "typing_chars": (10000, 18000),
        "focus_ratio": (0.5, 0.7),
        "context_switch_rate": (35, 55),
        "shortcuts_per_hour": (30, 60),
        "unique_apps": (6, 10),
        "coding_pct": (25, 35),
        "browsing_pct": (25, 35),
        "documentation_pct": (15, 25)
    },
    "moderate": {
        "work_hours": (6, 8),
        "productivity_score": (35, 55),
        "active_pct": (45, 60),
        "idle_pct": (25, 35),
        "pause_pct": (15, 20),
        "typing_chars": (6000, 12000),
        "focus_ratio": (0.3, 0.5),
        "context_switch_rate": (55, 80),
        "shortcuts_per_hour": (15, 35),
        "unique_apps": (5, 8),
        "coding_pct": (15, 25),
        "browsing_pct": (30, 45),
        "documentation_pct": (10, 20)
    },
    "weak": {
        "work_hours": (5, 7),
        "productivity_score": (10, 35),
        "active_pct": (30, 45),
        "idle_pct": (35, 50),
        "pause_pct": (15, 25),
        "typing_chars": (3000, 8000),
        "focus_ratio": (0.1, 0.3),
        "context_switch_rate": (80, 120),
        "shortcuts_per_hour": (5, 20),
        "unique_apps": (4, 7),
        "coding_pct": (5, 15),
        "browsing_pct": (40, 60),
        "documentation_pct": (5, 15)
    }
}

APPS_BY_CATEGORY = {
    "Coding": ["Code.exe", "PyCharm.exe", "IntelliJ.exe"],
    "Browsing": ["chrome.exe", "msedge.exe", "firefox.exe"],
    "Documentation": ["WINWORD.EXE", "EXCEL.EXE", "Notepad.exe"],
    "Research": ["chrome.exe", "Acrobat.exe"],
    "Analysis": ["EXCEL.EXE", "Tableau.exe"],
    "Entertainment": ["chrome.exe", "Spotify.exe"],
    "Presentation": ["POWERPNT.EXE"],
    "Other": ["explorer.exe", "cmd.exe", "Teams.exe", "OUTLOOK.EXE"]
}

WINDOWS_BY_LEVEL = {
    "excellent": [
        "AWS Console - Google Chrome",
        "Terraform Configuration - Visual Studio Code",
        "Kubernetes Dashboard - Google Chrome",
        "Architecture Design.pptx - PowerPoint",
        "CloudFormation Template.yaml - Visual Studio Code",
        "Docker Dashboard - Google Chrome",
        "Python Script - Visual Studio Code",
        "Jenkins Pipeline - Google Chrome"
    ],
    "good": [
        "AWS EC2 Dashboard - Google Chrome",
        "Python Script - Visual Studio Code",
        "Jenkins Pipeline - Google Chrome",
        "Documentation.md - Visual Studio Code",
        "GitHub Pull Request - Google Chrome",
        "Team Meeting - Microsoft Teams",
        "Email - Outlook"
    ],
    "moderate": [
        "Google Search - Google Chrome",
        "Stack Overflow - Google Chrome",
        "Tutorial Video - Google Chrome",
        "Simple Script.py - Visual Studio Code",
        "Inbox - Outlook",
        "Slack - General Channel"
    ],
    "weak": [
        "YouTube - How to Cloud - Google Chrome",
        "Facebook - Google Chrome",
        "Reddit - Google Chrome",
        "Twitter - Google Chrome",
        "Inbox (2500 unread) - Outlook",
        "Downloads - File Explorer"
    ]
}

def generate_kpi_summary(emp_id, date, profile_level):
    """Generate a complete KPI summary document matching your real data structure"""
    
    profile = PERFORMANCE_PROFILES[profile_level]
    
    # Calculate work duration
    work_hours = random.uniform(*profile["work_hours"])
    total_min = work_hours * 60
    
    # Calculate time percentages
    active_pct = random.uniform(*profile["active_pct"])
    idle_pct = random.uniform(*profile["idle_pct"])
    pause_pct = random.uniform(*profile["pause_pct"])
    
    active_min = (active_pct / 100) * total_min
    idle_min = (idle_pct / 100) * total_min
    pause_min = (pause_pct / 100) * total_min
    
    # Generate typing data
    total_keystrokes = random.randint(*profile["typing_chars"])
    
    # Distribute across work hours
    work_start_hour = 15  # 3 PM
    work_end_hour = work_start_hour + int(work_hours)
    
    typing_per_hour = []
    keystrokes_per_active_hour = []
    for hour in range(work_start_hour, work_end_hour + 1):
        chars = int(total_keystrokes / work_hours) + random.randint(-500, 500)
        typing_per_hour.append({
            "hour": hour,
            "chars_per_hour": max(0, chars)
        })
        keystrokes_per_active_hour.append({
            "hour": hour,
            "keystrokes": random.randint(40, 80)
        })
    
    # Generate idle per hour
    idle_per_hour = []
    for hour in range(work_start_hour, work_end_hour + 1):
        idle_min_hour = (idle_min / work_hours) + random.uniform(-5, 5)
        idle_per_hour.append({
            "hour": hour,
            "idle_min_per_hour": max(0, idle_min_hour)
        })
    
    # Generate app usage
    apps = []
    for category, app_list in APPS_BY_CATEGORY.items():
        apps.extend(app_list)
    
    unique_apps_count = random.randint(*profile["unique_apps"])
    selected_apps = random.sample(list(set(apps)), min(unique_apps_count, len(set(apps))))
    
    idle_per_app = []
    active_per_app = []
    for app in selected_apps:
        idle_per_app.append({
            "application": app,
            "idle_min": random.uniform(0.1, idle_min / len(selected_apps))
        })
        active_per_app.append({
            "application": app,
            "keystroke_count": random.randint(1, 500)
        })
    
    # Generate app usage per hour
    app_usage_per_hour = []
    for app in selected_apps:
        for hour in range(work_start_hour, work_end_hour + 1):
            if random.random() < 0.7:  # 70% chance app used in this hour
                app_usage_per_hour.append({
                    "application": app,
                    "hour": hour,
                    "events_per_hour": random.randint(5, 200)
                })
    
    # Generate pause data
    pause_count = random.randint(1, 4)
    pause_reasons = ["Bathroom", "Meeting", "Lunch", "Coffee Break"]
    pause_per_hour = []
    avg_pause_duration = pause_min / pause_count if pause_count > 0 else 0
    
    for i in range(pause_count):
        pause_per_hour.append({
            "hour": random.randint(work_start_hour, work_end_hour),
            "reason": random.choice(pause_reasons),
            "pause_count": 1,
            "pause_total_min": pause_min / pause_count
        })
    
    # Generate shortcuts data
    total_shortcuts = random.randint(*profile["shortcuts_per_hour"]) * int(work_hours)
    shortcuts_used = [{"shortcut": "Switch App", "count": total_shortcuts}]
    
    shortcuts_per_hour = []
    for hour in range(work_start_hour, work_end_hour + 1):
        shortcuts_per_hour.append({
            "hour": hour,
            "shortcut": "Switch App",
            "count": int(total_shortcuts / work_hours)
        })
    
    # Generate top windows
    windows = WINDOWS_BY_LEVEL[profile_level]
    top_windows = []
    window_switch_count = random.randint(150, 500)
    
    for i, window in enumerate(random.sample(windows, min(5, len(windows)))):
        top_windows.append({
            "window": window,
            "switch_count": int(window_switch_count / (i + 1.5))
        })
    
    # Generate donut chart (time per category)
    coding_pct = random.uniform(*profile["coding_pct"])
    browsing_pct = random.uniform(*profile["browsing_pct"])
    documentation_pct = random.uniform(*profile["documentation_pct"])
    
    remaining_pct = 100 - (coding_pct + browsing_pct + documentation_pct)
    
    donut_chart = [
        {"category": "Coding", "minutes": (coding_pct / 100) * total_min},
        {"category": "Browsing", "minutes": (browsing_pct / 100) * total_min},
        {"category": "Documentation", "minutes": (documentation_pct / 100) * total_min},
        {"category": "Research", "minutes": (remaining_pct * 0.4 / 100) * total_min},
        {"category": "Analysis", "minutes": (remaining_pct * 0.15 / 100) * total_min},
        {"category": "Entertainment", "minutes": (remaining_pct * 0.25 / 100) * total_min},
        {"category": "Presentation", "minutes": (remaining_pct * 0.1 / 100) * total_min},
        {"category": "Other", "minutes": (remaining_pct * 0.1 / 100) * total_min}
    ]
    
    # Calculate metrics
    focus_ratio = random.uniform(*profile["focus_ratio"])
    context_switch_rate = random.uniform(*profile["context_switch_rate"])
    productivity_score = random.uniform(*profile["productivity_score"])
    
    # Generate session data
    session_start = datetime.combine(date, datetime.min.time().replace(hour=work_start_hour))
    session_end = session_start + timedelta(hours=work_hours)
    
    sessions = [{
        "session_id": str(uuid.uuid4()),
        "session_start": int(session_start.timestamp() * 1000),
        "session_end": int(session_end.timestamp() * 1000),
        "session_duration_min": total_min,
        "active_min": active_min,
        "idle_min": idle_min,
        "pause_min": pause_min
    }]
    
    # Build the complete KPI document
    kpi_doc = {
        "employee_id": emp_id,
        "date": date.strftime("%Y-%m-%d"),
        "doc_id": f"{emp_id}-{date.strftime('%Y-%m-%d')}",
        
        # Typing metrics
        "total_keystrokes": total_keystrokes,
        "typing_per_hour": typing_per_hour,
        "keystrokes_per_active_hour": keystrokes_per_active_hour,
        "typing_chars": total_keystrokes,
        
        # Time metrics
        "total_min": total_min,
        "active_min": active_min,
        "idle_min": idle_min,
        "pause_min": pause_min,
        "total_idle_min": idle_min,
        "pause_total_min": pause_min,
        "active_pct": active_pct,
        "idle_pct": idle_pct,
        "pause_pct": pause_pct,
        "active_hours": work_hours,
        
        # Idle data
        "idle_per_hour": idle_per_hour,
        "idle_per_app": idle_per_app,
        
        # Pause data
        "pause_count": pause_count,
        "pause_per_hour": pause_per_hour,
        "avg_pause_duration_min": avg_pause_duration,
        
        # Shortcuts
        "shortcuts_used": shortcuts_used,
        "shortcuts_per_hour": shortcuts_per_hour,
        
        # App usage
        "active_per_app": active_per_app,
        "app_usage_per_hour": app_usage_per_hour,
        "unique_apps_count": unique_apps_count,
        
        # Windows
        "top_windows": top_windows,
        "window_switch_count": window_switch_count,
        
        # Sessions
        "sessions": sessions,
        "heartbeat_count": int(total_min / 5),  # Every 5 minutes
        
        # Time breakdown
        "donut_chart": donut_chart,
        
        # Calculated metrics
        "focus_ratio": focus_ratio,
        "context_switch_rate": context_switch_rate,
        "productivity_score": productivity_score,
        
        # Normalized scores (between -1 and 1)
        "focus_norm": (focus_ratio - 0.5) * 2,
        "idle_norm": -((idle_pct - 25) / 25),
        "context_norm": -((context_switch_rate - 50) / 50),
        "event_div_norm": 1.0,
        
        # Additional fields
        "active_events": int(total_keystrokes / 10),
        "distinct_event_types": random.randint(6, 10)
    }
    
    return kpi_doc

def main():
    print("🚀 Starting KPI Summary Generation for Cloud Team (Nov 3-7, 2025)...")
    
    index_name = "employee_kpi_summary4"
    
    # Check if index exists
    if not es.indices.exists(index=index_name):
        print(f"Creating index: {index_name}")
        es.indices.create(index=index_name)
    
    # Generate KPI summaries for each employee for the week
    dates = [datetime(2025, 11, 3) + timedelta(days=i) for i in range(5)]  # Mon-Fri
    
    total_docs = 0
    for emp_id, emp_info in EMPLOYEES.items():
        print(f"\n👤 Generating KPI summaries for {emp_info['name']} ({emp_info['role']}) - Level: {emp_info['level'].upper()}")
        
        for date in dates:
            kpi_doc = generate_kpi_summary(emp_id, date, emp_info["level"])
            
            # Insert into Elasticsearch
            doc_id = kpi_doc["doc_id"]
            es.index(index=index_name, id=doc_id, body=kpi_doc)
            
            print(f"   📅 {date.strftime('%Y-%m-%d (%A)')}: ✅ Productivity Score: {kpi_doc['productivity_score']:.1f}")
            total_docs += 1
    
    print("\n" + "="*60)
    print("📊 KPI GENERATION SUMMARY")
    print("="*60)
    for emp_id, emp_info in EMPLOYEES.items():
        print(f"{emp_info['name']:25} | {emp_info['role']:25} | {emp_info['level'].upper()}")
    print("="*60)
    print(f"Total Documents: {total_docs}")
    print(f"Date Range: November 3-7, 2025 (5 days)")
    print(f"Elasticsearch Index: {index_name}")
    print("="*60)
    print("\n✅ All KPI summaries generated successfully!")
    print("🎯 Your dashboard should now display the data.")

if __name__ == "__main__":
    main()