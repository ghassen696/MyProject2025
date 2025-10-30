import { HourlyKeystrokes } from '../../types/Employee-kpi';

interface Props {
  data: HourlyKeystrokes[];
}

export default function HourlyKeystrokesChart({ data }: Props) {
  const maxKeystrokes = Math.max(...data.map(d => d.keystrokes));
  const workingHoursData = data.filter(d => d.hour >= 8 && d.hour <= 18);
  //const workingHoursData = data;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-xl font-bold text-gray-900 mb-6">Keystrokes by Hour</h3>
      <div className="flex items-end justify-between space-x-2 h-48">
        {workingHoursData.map(item => (
          <div key={item.hour} className="flex flex-col items-center flex-1">
            <div 
              className="bg-gradient-to-t from-blue-500 to-blue-400 rounded-t w-full min-h-1 transition-all duration-500 hover:from-blue-600 hover:to-blue-500 shadow-sm"
              style={{ height: `${maxKeystrokes > 0 ? (item.keystrokes / maxKeystrokes) * 160 : 0}px` }}
              title={`${item.keystrokes} keystrokes at ${item.hour}:00`}
            />
            <div className="text-xs text-gray-600 mt-3 font-medium">{item.hour}:00</div>
            <div className="text-xs font-bold text-blue-600">{item.keystrokes}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
