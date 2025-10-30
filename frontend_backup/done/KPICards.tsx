import { Keyboard, Clock, Pause, TrendingUp, BarChart3, Timer } from 'lucide-react';
import { ProcessedEmployeeData } from '../../types/Employee-kpi';

interface Props {
  employee: ProcessedEmployeeData;
}

export default function KPICards({ employee }: Props) {
  const cards = [
    { title: 'Total Keystrokes', value: employee.total_keystrokes, icon: Keyboard, color: 'bg-gradient-to-r from-blue-500 to-blue-600', textColor: 'text-blue-600', bgColor: 'bg-blue-50' },
    { title: 'Idle Minutes', value: employee.total_idle_minutes.toFixed(2), icon: Clock, color: 'bg-gradient-to-r from-yellow-500 to-yellow-600', textColor: 'text-yellow-600', bgColor: 'bg-yellow-50' },
    { title: 'Total Pauses', value: employee.total_pauses.toString(), icon: Pause, color: 'bg-gradient-to-r from-red-500 to-red-600', textColor: 'text-red-600', bgColor: 'bg-red-50' },
    { title: 'Pause Minutes', value: employee.total_pause_minutes.toFixed(2), icon: Timer, color: 'bg-gradient-to-r from-orange-500 to-orange-600', textColor: 'text-orange-600', bgColor: 'bg-orange-50' },
    { title: 'Keystrokes per Min', value: employee.keystrokes_per_minute.toFixed(2), icon: TrendingUp, color: 'bg-gradient-to-r from-green-500 to-green-600', textColor: 'text-green-600', bgColor: 'bg-green-50' },
    { title: 'Active Minutes', value: employee.active_minutes.toFixed(2), icon: BarChart3, color: 'bg-gradient-to-r from-purple-500 to-purple-600', textColor: 'text-purple-600', bgColor: 'bg-purple-50' },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-8">
      {cards.map((card, idx) => (
        <div key={idx} className={`${card.bgColor} rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-all duration-200`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-700 mb-1">{card.title}</p>
              <p className={`text-2xl font-bold ${card.textColor} mt-1`}>{card.value}</p>
            </div>
            <div className={`${card.color} rounded-xl p-3 shadow-lg`}>
              <card.icon className="w-4 h-4 text-white" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
