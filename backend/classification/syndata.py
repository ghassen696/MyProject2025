import random
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
