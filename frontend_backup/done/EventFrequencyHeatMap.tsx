import { Event } from '../../types/Employee-kpi';

interface Props {
  events: Event[];
}

const EVENT_TYPES = ['keystrokes', 'window_switch', 'pause', 'resume', 'clipboard_paste', 'shortcut'];

export default function EventFrequencyHeatmap({ events }: Props) {
  const hours = Array.from({ length: 10 }, (_, i) => i + 9); 

  //const hours = Array.from({ length: 24 }, (_, i) => i);

  // Build a map: eventType -> hour -> count
  const counts: Record<string, Record<number, number>> = {};
  EVENT_TYPES.forEach(type => {
    counts[type] = {};
    hours.forEach(h => counts[type][h] = 0);
  });

  events.forEach(ev => {
    if (EVENT_TYPES.includes(ev.event)) {
      const hour = new Date(ev.timestamp).getUTCHours();
      counts[ev.event][hour] += 1;
    }
  });

  const getIntensityColor = (value: number, max: number) => {
    if (value === 0) return 'bg-gray-100';
    const intensity = (value / max) * 100;
    if (intensity < 20) return 'bg-blue-100';
    if (intensity < 40) return 'bg-blue-200';
    if (intensity < 60) return 'bg-blue-300';
    if (intensity < 80) return 'bg-blue-400';
    return 'bg-blue-500';
  };

  const getTextColor = (value: number, max: number) => ((value / max) * 100 > 60 ? 'text-white' : 'text-gray-700');

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 overflow-x-auto">
      <h3 className="text-xl font-bold text-gray-900 mb-4">Event Type Frequency Heatmap</h3>
      
      {/* Header: hours */}
      <div className="flex mb-2">
        <div className="w-28"></div>
        {hours.map(hour => (
          <div key={hour} className="w-8 text-xs text-gray-500 text-center">{hour}</div>
        ))}
      </div>

      {/* Rows: event types */}
      {EVENT_TYPES.map(type => {
        const maxCount = Math.max(...Object.values(counts[type]), 1);
        return (
          <div key={type} className="flex items-center mb-1">
            <div className="w-28 text-sm font-medium text-gray-700 pr-2">{type}</div>
            {hours.map(hour => {
              const value = counts[type][hour];
              const colorClass = getIntensityColor(value, maxCount);
              const textColor = getTextColor(value, maxCount);
              return (
                <div
                  key={`${type}-${hour}`}
                  className={`w-8 h-8 mr-1 rounded ${colorClass} ${textColor} flex items-center justify-center text-xs font-medium cursor-pointer`}
                  title={`${type} ${hour}:00 - ${value} events`}
                >
                  {value > 0 ? value : ''}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
