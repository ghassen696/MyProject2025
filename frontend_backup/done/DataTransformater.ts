import { ElasticsearchResponse, ProcessedEmployeeData, EventTypeCounts, HourlyKeystrokes, HeatmapData, EmployeeSummary } from '../types/Employee-kpi';

export const transformElasticsearchData = (response: ElasticsearchResponse): ProcessedEmployeeData[] => {
  return response.hits.hits.map(hit => {
    const source = hit._source;
    const activeMinutes = source.active_minutes;
    const productivityScore = Math.min(100, Math.round((activeMinutes / (8 * 60)) * 100));
    
    return {
      employee_id: source.employee_id,
      employee_status: source.employee_status,
      last_event_time: source.last_event_time,
      total_keystrokes: source.keystrokes_today,
      total_idle_minutes: Math.round(source.total_idle_today / 60),
      total_pauses: source.pauses_today,
      total_pause_minutes: Math.round(source.total_pause_minutes_today),
      keystrokes_per_minute: source.keystrokes_per_minute,
      events_today: source.events_today,
      active_minutes: source.active_minutes,
      productivity_score: productivityScore
    };
  });
};

export const generateEmployeeSummaries = (employees: ProcessedEmployeeData[]): EmployeeSummary[] => {
  return employees.map(emp => ({
    employee_id: emp.employee_id,
    status: emp.employee_status,
    keystrokes: emp.total_keystrokes,
    active_minutes: emp.active_minutes,
    productivity_score: emp.productivity_score,
    last_activity: emp.last_event_time
  }));
};

export const generateHeatmapData = (events: Event[]): HeatmapData[] => {
  const hours = Array.from({ length: 24 }, (_, i) => i); // 0-23
  const dayLabel = 'Today'; // single day

  // Initialize all 24 hours with 0
  const heatmapCells: HeatmapData[] = hours.map(hour => ({
    day: dayLabel,
    hour,
    events: 0,
    value: 0,
  }));

  // Count events per hour
  const counts: Record<number, number> = {};
  events.forEach(ev => {
    const hour = new Date(ev.timestamp).getUTCHours(); // adjust timezone if needed
    counts[hour] = (counts[hour] || 0) + 1;
  });

  const maxEvents = Math.max(...Object.values(counts), 1);

  // Assign counts and compute intensity
  heatmapCells.forEach(cell => {
    const cellCount = counts[cell.hour] || 0;
    cell.events = cellCount;
    cell.value = Math.round((cellCount / maxEvents) * 100); // intensity 0-100%
  });

  return heatmapCells;
};

export const getEventTypeCounts = (events: { event: string; timestamp: number }[]) => {
  return events.reduce((acc, ev) => {
    acc[ev.event] = (acc[ev.event] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);
};

export const generateHourlyKeystrokes = (
  totalKeystrokes: number,
  events: { event: string; timestamp: number }[]
): HourlyKeystrokes[] => {
  const hourly: Record<number, number> = {};

  // Count keystrokes by hour
  events.forEach(ev => {
    if (ev.event === "keystrokes") {
      const hour = new Date(ev.timestamp).getUTCHours();
      hourly[hour] = (hourly[hour] || 0) + 1;
    }
  });
  console.log("Keystrokes per hour:", events.map(ev => ({
    timestamp: ev.timestamp,
    hour: new Date(ev.timestamp).getUTCHours(),
    event: ev.event
  })));
  // Build output for 24h
  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    keystrokes: hourly[hour] || 0,
  }));
};
export const formatTimestamp = (timestamp: number): string => {
  return new Date(timestamp).toUTCString();
};

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'active': return 'text-green-600 bg-green-100';
    case 'idle': return 'text-yellow-600 bg-yellow-100';
    case 'paused': return 'text-red-600 bg-red-100';
    default: return 'text-gray-600 bg-gray-100';
  }
};

function transformPauseData(apiData: any[]): PauseHourlyData[] {
  const hoursMap: Record<number, PauseHourlyData> = {};

  apiData.forEach(item => {
    const hour = item.hour;
    if (!hoursMap[hour]) {
      hoursMap[hour] = {
        hour,
        personalBreak: 0,
        lunch: 0,
        bathroom: 0,
        meeting: 0,
        phoneCall: 0,
        other: 0
      };
    }

    switch (item.reason) {
      case 'Personal break':
        hoursMap[hour].personalBreak = item.pause_total_min;
        break;
      case 'Lunch':
        hoursMap[hour].lunch = item.pause_total_min;
        break;
      case 'Bathroom':
        hoursMap[hour].bathroom = item.pause_total_min;
        break;
      case 'Meeting':
        hoursMap[hour].meeting = item.pause_total_min;
        break;
      case 'Phone call':
        hoursMap[hour].phoneCall = item.pause_total_min;
        break;
      default:
        hoursMap[hour].other = item.pause_total_min;
        break;
    }
  });

  return Object.values(hoursMap).sort((a, b) => a.hour - b.hour);
}
export { transformPauseData };