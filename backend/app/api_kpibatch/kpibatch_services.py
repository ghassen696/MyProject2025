from collections import defaultdict
from .models import (
    ProductivityData, HourlyValue, AppUsage, PauseHourlyData,
    ShortcutUsed, ShortcutPerHour, TopWindow, Session, DonutCategory,
    AppUsagePerHour
)

from collections import defaultdict
from datetime import datetime

from collections import defaultdict

def rollup_productivity(docs: list):
    if not docs:
        return {}

    n = len(docs)
    summary = defaultdict(float)
    daily_trends = defaultdict(list)
    app_usage = defaultdict(int)

    for doc in docs:
        # Compute total minutes dynamically (since total_min is not stored)
        total_min = doc.active_min + doc.idle_min + doc.pause_min

        # ---- Summary ----
        summary['productivity_score'] += doc.productivity_score
        summary['active_min'] += doc.active_min
        summary['idle_min'] += doc.idle_min

        # Idle percentage safely computed
        summary['idle_pct'] += (doc.idle_min / total_min * 100) if total_min else 0

        # ---- Daily Trends ----
        date = doc.date
        daily_trends['productivity'].append({
            'date': date,
            'value': doc.productivity_score
        })
        daily_trends['idle_pct'].append({
            'date': date,
            'value': (doc.idle_min / total_min * 100) if total_min else 0
        })
        daily_trends['keystrokes'].append({
            'date': date,
            'value': doc.total_keystrokes
        })

        # ---- App Usage Roll-up ----
        for app in doc.active_per_app:
            app_usage[app.app_name] += app.value

    # ---- Averages ----
    summary['avg_productivity_score'] = summary['productivity_score'] / n
    summary['avg_idle_pct'] = summary['idle_pct'] / n

    # ---- Top Apps ----
    top_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)

    return {
        'summary': summary,
        'daily_trends': daily_trends,
        'top_apps': top_apps
    }


def transform_es_doc(doc: dict) -> ProductivityData:
    src = doc["_source"]

    # Typing per hour
    typing_per_hour = [
        HourlyValue(hour=e["hour"], value=e.get("chars_per_hour", 0))
        for e in src.get("typing_per_hour", [])
    ]

    keystrokes_per_active_hour = [
        HourlyValue(hour=e["hour"], value=e.get("keystrokes", 0))
        for e in src.get("keystrokes_per_active_hour", [])
    ]

    idle_per_hour = [
        HourlyValue(hour=e["hour"], value=e.get("idle_min_per_hour", 0))
        for e in src.get("idle_per_hour", [])
    ]

    # Idle per app with percentage
    total_idle = sum(a["idle_min"] for a in src.get("idle_per_app", []))
    idle_per_app = [
        AppUsage(
            app_name=a["application"],
            value=a["idle_min"],
            percentage=(a["idle_min"] / total_idle * 100 if total_idle > 0 else 0)
        )
        for a in src.get("idle_per_app", [])
    ]

    # Map pause reasons into unified structure
    reason_map = {
        "Meeting": "meeting",
        "Phone call": "phoneCall",
        "Lunch": "lunch",
        "Bathroom": "bathroom",
        "Break": "personalBreak"
    }

    hourly_pauses = defaultdict(lambda: {
        "hour": 0,
        "meeting": 0.0,
        "phoneCall": 0.0,
        "lunch": 0.0,
        "bathroom": 0.0,
        "personalBreak": 0.0,
        "other": 0.0
    })

    for e in src.get("pause_per_hour", []):
        hour = e.get("hour", 0)
        reason = reason_map.get(e.get("reason", ""), "other")
        hourly_pauses[hour]["hour"] = hour
        hourly_pauses[hour][reason] += e.get("pause_total_min", 0)

    pause_per_hour = [PauseHourlyData(**vals) for vals in hourly_pauses.values()]

    # Shortcuts
    shortcuts_used = [
        ShortcutUsed(
            shortcut=s["shortcut"],
            count=s["count"],
            description=s.get("description")
        )
        for s in src.get("shortcuts_used", [])
    ]

    shortcuts_per_hour = [
        ShortcutPerHour(
            hour=e["hour"],
            shortcut=e.get("shortcut", ""),
            count=e.get("count", 0)
        )
        for e in src.get("shortcuts_per_hour", [])
    ]

    # Active per app with percentage
    total_active = sum(a["keystroke_count"] for a in src.get("active_per_app", []))
    active_per_app = [
        AppUsage(
            app_name=a["application"],
            value=a["keystroke_count"],
            percentage=(a["keystroke_count"] / total_active * 100 if total_active > 0 else 0)
        )
        for a in src.get("active_per_app", [])
    ]

    # App usage per hour grouped
    apps_by_hour = defaultdict(dict)
    for e in src.get("app_usage_per_hour", []):
        apps_by_hour[e["hour"]][e["application"]] = e["events_per_hour"]
    app_usage_per_hour = [AppUsagePerHour(hour=h, apps=apps) for h, apps in apps_by_hour.items()]

    # Top windows (merge with time_per_window if exists)
    time_map = {w["window"]: w.get("time_spent_min", 0) for w in src.get("time_per_window", [])
        if w.get("window")  # skip empty dicts or missing keys
}
    top_windows = [
        TopWindow(
            window_title=w.get("window", "Unknown"),
            switch_count=w.get("switch_count", 0),
            time_spent=time_map.get(w.get("window"),0)
        )
        for w in src.get("top_windows", [])
    ]

    # Sessions
    sessions = [
        Session(
            session_id=s.get("session_id"),
            start_time=s.get("session_start", 0),
            end_time=s.get("session_end", 0),
            session_duration_min=s.get("session_duration_min", 0),
            active_duration=s.get("active_min", 0),
            idle_duration=s.get("idle_min", 0),
            pause_duration=s.get("pause_min", 0),
            session_type="work"
        )
        for s in src.get("sessions", [])
    ]

    # Donut chart
    donut_chart = [
        DonutCategory(category=app["category"], minutes=app["minutes"])
        for app in src.get("donut_chart", [])
    ]

    return ProductivityData(
        employee_id=src["employee_id"],
        date=src["date"],
        total_keystrokes=src.get("total_keystrokes", 0),
        active_min=sum(s.get("active_min", 0) for s in src.get("sessions", [])),
        idle_min=src.get("idle_min", 0),
        pause_min=src.get("pause_min", 0),
        productivity_score=src.get("productivity_score", 0),
        focus_ratio=src.get("focus_norm", 0),
        shortcut_count=src.get("shortcut_count", 0),
        heartbeat_count=src.get("heartbeat_count", 0),

        typing_per_hour=typing_per_hour,
        keystrokes_per_active_hour=keystrokes_per_active_hour,
        idle_per_hour=idle_per_hour,
        idle_per_app=idle_per_app,
        pause_per_hour=pause_per_hour,
        pause_total_min=src.get("pause_total_min", 0),
        avg_pause_duration_min=src.get("avg_pause_duration_min", 0),

        shortcuts_used=shortcuts_used,
        shortcuts_per_hour=shortcuts_per_hour,
        active_per_app=active_per_app,
        app_usage_per_hour=app_usage_per_hour,

        top_windows=top_windows,
        window_switch_count=src.get("window_switch_count", 0),
        context_switch_rate=src.get("context_switch_rate", 0),
        sessions=sessions,

        unique_apps_count=src.get("unique_apps_count", 0),
        distinct_event_types=src.get("distinct_event_types", 0),
        active_events=src.get("active_events", 0),
        donut_chart=donut_chart
    )
