import { EventTypeCounts } from '../../types/Employee-kpi';

interface Props {
  eventCounts: EventTypeCounts;
}

export default function EventDistributionChart({ eventCounts }: Props) {
  const total = Object.values(eventCounts).reduce((sum, count) => sum + count, 0);
  
  const colors = [
    '#3B82F6', '#8B5CF6', '#EF4444', '#10B981', '#F59E0B', 
    '#6B7280', '#EC4899', '#14B8A6', '#F97316', '#84CC16'
  ];

  const data = Object.entries(eventCounts)
    .sort(([,a], [,b]) => b - a)
    .slice(0, 8);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <h3 className="text-xl font-bold text-gray-900 mb-6">Event Distribution</h3>
      
      <div className="relative">
        <div className="space-y-1">
          {data.map(([eventType, count], index) => {
            const percentage = (count / total) * 100;
            return (
              <div key={eventType} className="hover:bg-gray-50 p-2 rounded-lg transition-colors">
                <div className="flex items-center space-x-3">
                  <div 
                    className="w-4 h-4 rounded-full shadow-sm"
                    style={{ backgroundColor: colors[index] }}
                  />
                  <div className="flex-1">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-medium text-gray-900 capitalize">
                        {eventType.replace('_', ' ')}
                      </span>
                      <span className="font-semibold text-gray-700">
                        {count} ({percentage.toFixed(1)}%)
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1">
                      <div 
                        className="h-2 rounded-full transition-all duration-500 ease-out"
                        style={{ 
                          backgroundColor: colors[index], 
                          width: `${percentage}%` 
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
