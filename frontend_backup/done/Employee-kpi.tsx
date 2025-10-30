export interface ProcessedEmployeeData {
  employee_id: string;
  employee_status: string;
  last_event_time: number;
  total_keystrokes: number;
  total_idle_minutes: number;
  total_pauses: number;
  total_pause_minutes: number;
  keystrokes_per_minute: number;
  events_today: string[];
  active_minutes: number;
  productivity_score: number;
}

export interface EventTypeCounts {
  [eventType: string]: number;
}

export interface HourlyKeystrokes {
  hour: number;
  keystrokes: number;
}

export interface HeatmapData {
  hour: number;
  day: string;
  value: number; // intensity
  events: number;
}
export interface Event {
  event: string;
  timestamp: number; // milliseconds since epoch
}

export interface EmployeeSummary {
  employee_id: string;
  status: string;
  keystrokes: number;
  active_minutes: number;
  productivity_score: number;
  last_activity: number;
  keystrokes_per_minute: number;


}
// types/Employee-kpi.ts
export interface ActivityLog {
  timestamp: number;        // epoch timestamp
  event: string;            // e.g., "keystrokes", "pause", "resume", "window_switch", etc.
  employee_id: string;
  session_id?: string;
  window?: string;
  application?: string;
  control?: string;
  text?: string;
  reason?: string;          // for "pause" events
  duration_minutes?: number; // for "pause" events
  shortcut_name?: string;   // for "shortcut" events
  status?: string;          // for "heartbeat" events
  seq_num?: number;
}
