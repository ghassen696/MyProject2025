
"""from collections import defaultdict
from .models import (
    ProductivityData, HourlyValue, AppUsage, PauseHourlyData,
    ShortcutUsed, ShortcutPerHour, TopWindow, Session, DonutCategory,
    AppUsagePerHour
)


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
        DonutCategory(category=app["category"], count=app["count"])
        for app in src.get("donut_chart", [])
    ]

    return ProductivityData(
        employee_id=src["employee_id"],
        date=src["date"],
        total_keystrokes=src.get("total_keystrokes", 0),
        active_min=src.get("active_min", 0),
        idle_min=src.get("idle_min", 0),
        pause_min=src.get("pause_min", 0),
        productivity_score=src.get("productivity_score", 0),
        focus_ratio=src.get("focus_ratio", 0),
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
"""
# kpibatch_services.py
from collections import defaultdict
from .models import (
    ProductivityData, HourlyValue, AppUsage, PauseHourlyData,
    ShortcutUsed, ShortcutPerHour, TopWindow, Session, DonutCategory,
    AppUsagePerHour,DateRange
)
from statistics import mean
from typing import List



def transform_es_doc(doc: dict,start_date: str = None, end_date: str = None) -> ProductivityData:
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
        DonutCategory(category=app["category"], count=app["count"])
        for app in src.get("donut_chart", [])
    ]

    if start_date and end_date:
        date_range = {"from_date": start_date, "to_date": end_date}
    else:
        date_str = hit.get("date")
        date_range = {"from_date": date_str, "to_date": date_str}
    return ProductivityData(
        employee_id=src["employee_id"],
        date=DateRange(**date_range),
        total_keystrokes=src.get("total_keystrokes", 0),
        active_min=src.get("active_min", 0),
        idle_min=src.get("idle_min", 0),
        pause_min=src.get("pause_min", 0),
        productivity_score=src.get("productivity_score", 0),
        focus_ratio=src.get("focus_ratio", 0),
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


def aggregate_productivity_docs(docs: List[ProductivityData]) -> ProductivityData:
    if not docs:
        raise ValueError("No documents to aggregate")

    docs = sorted(docs, key=lambda d: d.date)

    numeric_avg = ["productivity_score", "focus_ratio", "context_switch_rate", "avg_pause_duration_min"]
    cumulative = ["total_keystrokes", "active_min", "idle_min", "pause_min",
                  "shortcut_count", "heartbeat_count", "pause_total_min", "window_switch_count"]

    avg_vals = {field: mean(getattr(d, field, 0) for d in docs) for field in numeric_avg}
    cum_vals = {field: sum(getattr(d, field, 0) for d in docs) for field in cumulative}

    employee_id = "team" if len({d.employee_id for d in docs}) > 1 else docs[0].employee_id
    date_str = {"from": docs[0].date, "to": docs[-1].date} if len(docs) > 1 else docs[0].date

    # ----------------- Aggregate per-hour metrics -----------------
    def aggregate_hourly(list_of_hourly: List[List[HourlyValue]]) -> List[HourlyValue]:
        hourly_map = defaultdict(list)
        for hourly in list_of_hourly:
            for h in hourly:
                hourly_map[h.hour].append(h.value)
        return [HourlyValue(hour=hour, value=sum(values)) for hour, values in sorted(hourly_map.items())]

    typing_per_hour = aggregate_hourly([d.typing_per_hour for d in docs])
    keystrokes_per_active_hour = aggregate_hourly([d.keystrokes_per_active_hour for d in docs])
    idle_per_hour = aggregate_hourly([d.idle_per_hour for d in docs])

    # ----------------- Aggregate per-app metrics -----------------
    def aggregate_app_usage(list_of_apps: List[List[AppUsage]]) -> List[AppUsage]:
        app_map = defaultdict(float)
        for apps in list_of_apps:
            for a in apps:
                app_map[a.app_name] += a.value
        total = sum(app_map.values())
        return [AppUsage(app_name=name, value=val, percentage=(val/total*100 if total else 0))
                for name, val in sorted(app_map.items(), key=lambda x: x[1], reverse=True)]

    idle_per_app = aggregate_app_usage([d.idle_per_app for d in docs])
    active_per_app = aggregate_app_usage([d.active_per_app for d in docs])

    # ----------------- Aggregate app usage per hour -----------------
    app_usage_per_hour_map = defaultdict(lambda: defaultdict(int))
    for d in docs:
        for hour_entry in d.app_usage_per_hour:
            for app, count in hour_entry.apps.items():
                app_usage_per_hour_map[hour_entry.hour][app] += count
    app_usage_per_hour = [
        AppUsagePerHour(hour=h, apps=dict(sorted(apps.items(), key=lambda x: x[1], reverse=True)))
        for h, apps in sorted(app_usage_per_hour_map.items())
    ]

    # ----------------- Aggregate pause per hour -----------------
    pause_per_hour_map = defaultdict(lambda: defaultdict(float))
    hours_set = set()
    for d in docs:
        for p in d.pause_per_hour:
            hours_set.add(p.hour)
            for reason in ["personalBreak","lunch","bathroom","meeting","phoneCall","other"]:
                pause_per_hour_map[p.hour][reason] += getattr(p, reason, 0.0)
    pause_per_hour = [PauseHourlyData(hour=h, **pause_per_hour_map[h]) for h in sorted(hours_set)]

    # ----------------- Aggregate shortcuts -----------------
    shortcuts_count_map = defaultdict(lambda: {"count":0, "description":None})
    for d in docs:
        for s in d.shortcuts_used:
            shortcuts_count_map[s.shortcut]["count"] += s.count
            if s.description:
                shortcuts_count_map[s.shortcut]["description"] = s.description
    shortcuts_used = [ShortcutUsed(shortcut=k, count=v["count"], description=v["description"])
                      for k,v in sorted(shortcuts_count_map.items(), key=lambda x: x[1]["count"], reverse=True)]

    shortcuts_per_hour_map = defaultdict(lambda: defaultdict(int))
    for d in docs:
        for s in d.shortcuts_per_hour:
            shortcuts_per_hour_map[s.hour][s.shortcut] += s.count
    shortcuts_per_hour = [
        ShortcutPerHour(hour=h, shortcut=k, count=v)
        for h, apps in sorted(shortcuts_per_hour_map.items())
        for k, v in apps.items()
    ]

    # ----------------- Aggregate top windows -----------------
    top_window_map = defaultdict(lambda: {"switch_count":0,"time_spent":0.0})
    for d in docs:
        for w in d.top_windows:
            top_window_map[w.window_title]["switch_count"] += w.switch_count
            top_window_map[w.window_title]["time_spent"] += w.time_spent or 0.0
    top_windows = [TopWindow(window_title=k, switch_count=v["switch_count"], time_spent=v["time_spent"])
                   for k,v in sorted(top_window_map.items(), key=lambda x: x[1]["time_spent"], reverse=True)]

    # ----------------- Aggregate donut chart -----------------
    donut_map = defaultdict(int)
    for d in docs:
        for cat in d.donut_chart:
            donut_map[cat.category] += cat.count
    donut_chart = [DonutCategory(category=k, count=v) for k,v in sorted(donut_map.items(), key=lambda x: x[1], reverse=True)]

    # ----------------- Aggregate sessions -----------------
    sessions = []
    for d in docs:
        sessions.extend(d.sessions)

    # ----------------- Unique counts -----------------
    unique_apps = {a.app_name for d in docs for a in d.active_per_app}
    unique_event_types = {e for d in docs for e in range(d.distinct_event_types)}  # if you have event_type list, replace accordingly
    active_events_total = sum(d.active_events for d in docs)

    return ProductivityData(
        employee_id=employee_id,
        date=date_str,
        **avg_vals,
        **cum_vals,
        typing_per_hour=typing_per_hour,
        keystrokes_per_active_hour=keystrokes_per_active_hour,
        idle_per_hour=idle_per_hour,
        idle_per_app=idle_per_app,
        pause_per_hour=pause_per_hour,
        shortcuts_used=shortcuts_used,
        shortcuts_per_hour=shortcuts_per_hour,
        active_per_app=active_per_app,
        app_usage_per_hour=app_usage_per_hour,
        top_windows=top_windows,
        sessions=sessions,
        donut_chart=donut_chart,
        unique_apps_count=len(unique_apps),
        distinct_event_types=len(unique_event_types),
        active_events=active_events_total
    )
