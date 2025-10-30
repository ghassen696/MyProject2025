export interface Event {
  event: string;
  timestamp: number; // milliseconds since epoch
}
export interface EmployeeKPI {
  employee_id: string;
  date: number;
  total_idle_today: number; // seconds
  pauses_today: number;
  total_pause_minutes_today: number;
  keystrokes_today: number;
  last_idle_duration: number;
  keystrokes_per_minute: number;
  active_minutes: number;
  last_event_time: number;
  events_today: Event[];
  employee_status: string;
  doc_id: string;
}
