import { Clock, Keyboard, MousePointer, Pause, Copy, Zap } from 'lucide-react';

interface Event {
  event: string;
  timestamp: number;
}
interface Props {
  events: Event[];
}

export default function EventTimeline({ events }: Props) {
  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'keystrokes': return Keyboard;
      case 'window_switch': return MousePointer;
      case 'pause': return Pause;
      case 'clipboard_paste': return Copy;
      case 'shortcut': return Zap;
      default: return Clock;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'keystrokes': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'window_switch': return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'pause': return 'bg-red-100 text-red-800 border-red-200';
      case 'clipboard_paste': return 'bg-green-100 text-green-800 border-green-200';
      case 'shortcut': return 'bg-orange-100 text-orange-800 border-orange-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const recentEvents = events.slice(-20).reverse();

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-xl font-bold text-gray-900 mb-6">Recent Activity Timeline</h3>
      <div className="space-y-4 max-h-96 overflow-y-auto">
        {recentEvents.map((ev, index) => {
          const Icon = getEventIcon(ev.event);
          return (
            <div key={index} className="flex items-center space-x-4 hover:bg-gray-50 p-2 rounded-lg transition-colors">
              <div className={`p-3 rounded-full border ${getEventColor(ev.event)}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-gray-900 capitalize">{ev.event.replace('_', ' ')}</p>
                <p className="text-xs text-gray-500">{new Date(ev.timestamp).toUTCString()}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
