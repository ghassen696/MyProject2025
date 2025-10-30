from pydantic import BaseModel
from typing import List, Dict, Optional


class HourlyValue(BaseModel):
    hour: int
    value: float


class PausePerHour(BaseModel):
    hour: int
    reason: str
    pause_count: int
    pause_total_min: float


class PauseHourlyData(BaseModel):
    hour: int
    personalBreak: float
    lunch: float
    bathroom: float
    meeting: float
    phoneCall: float
    other: float


class ShortcutUsed(BaseModel):
    shortcut: str
    count: int
    description: Optional[str] = None


class ShortcutPerHour(BaseModel):
    hour: int
    shortcut: str
    count: int


class AppUsage(BaseModel):
    app_name: str
    value: float
    percentage: float


class DonutCategory(BaseModel):
    category: str
    count: int


class TopWindow(BaseModel):
    window_title: str
    switch_count: int
    time_spent: Optional[float] = None


class Session(BaseModel):
    session_id: Optional[str] = None
    start_time: float
    end_time: float
    session_duration_min: float
    active_duration: float
    idle_duration: float
    pause_duration: float
    session_type: str


class AppUsagePerHour(BaseModel):
    hour: int
    apps: Dict[str, int]

class ProductivityData(BaseModel):
    employee_id: str
    date: str
    total_keystrokes: int
    active_min: float
    idle_min: float
    pause_min: float
    productivity_score: float
    focus_ratio: float
    shortcut_count: int
    heartbeat_count: int

    typing_per_hour: List[HourlyValue]
    keystrokes_per_active_hour: List[HourlyValue]
    idle_per_hour: List[HourlyValue]
    idle_per_app: List[AppUsage]
    pause_per_hour: List[PauseHourlyData]
    pause_total_min: float
    avg_pause_duration_min: float

    shortcuts_used: List[ShortcutUsed]
    shortcuts_per_hour: List[ShortcutPerHour]

    active_per_app: List[AppUsage]
    app_usage_per_hour: List[AppUsagePerHour]

    top_windows: List[TopWindow]
    window_switch_count: int
    context_switch_rate: float
    sessions: List[Session]

    unique_apps_count: int
    distinct_event_types: int
    active_events: int
    donut_chart: List[DonutCategory]
