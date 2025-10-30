import React from 'react';
import { Monitor, BarChart3 } from 'lucide-react';
import { AppData, AppHourlyData } from '../../types/productivity-analytics';

interface ApplicationUsageProps {
  activePerApp: AppData[];
  appUsagePerHour: AppHourlyData[];
}

export default function ApplicationUsage({ activePerApp, appUsagePerHour }: ApplicationUsageProps) {
    if (
    !Array.isArray(activePerApp) ||
    activePerApp.length === 0 ||
    !Array.isArray(appUsagePerHour) ||
    appUsagePerHour.length === 0
  ) {
    return <div className="text-gray-500 text-center p-4">No data available</div>;
  }
  const colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6'];
  const topApps = Object.keys(appUsagePerHour?.[0]?.apps || {}).slice(0, 5);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* App Distribution Pie Chart */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center space-x-3 mb-6">
          <Monitor className="w-6 h-6 text-gray-700" />
          <h3 className="text-xl font-bold text-gray-900">Keystrokes by Application</h3>
        </div>
        
        <div className="flex items-center justify-center mb-6">
          <div className="relative w-48 h-48">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
              {activePerApp.map((app, index) => {
                const startAngle = activePerApp.slice(0, index).reduce((sum, a) => sum + (a.percentage * 3.6), 0);
                const endAngle = startAngle + (app.percentage * 3.6);
                const largeArcFlag = app.percentage > 50 ? 1 : 0;
                
                const x1 = 50 + 40 * Math.cos((startAngle * Math.PI) / 180);
                const y1 = 50 + 40 * Math.sin((startAngle * Math.PI) / 180);
                const x2 = 50 + 40 * Math.cos((endAngle * Math.PI) / 180);
                const y2 = 50 + 40 * Math.sin((endAngle * Math.PI) / 180);

                return (
                  <path
                    key={index}
                    d={`M 50 50 L ${x1} ${y1} A 40 40 0 ${largeArcFlag} 1 ${x2} ${y2} Z`}
                    fill={colors[index % colors.length]}
                    className="hover:opacity-80 transition-opacity cursor-pointer"
                  >
                    <title>{`${app.app_name}: ${app.value} keystrokes (${app.percentage.toFixed(1)}%)`}</title>
                  </path>
                );
              })}
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">
                  {activePerApp.reduce((sum, app) => sum + app.value, 0).toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">Total</div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="space-y-2">
          {activePerApp.map((app, index) => (
            <div key={index} className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div 
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: colors[index % colors.length] }}
                ></div>
                <span className="text-sm font-medium text-gray-700">{app.app_name}</span>
              </div>
              <div className="text-sm text-gray-600">
                {app.value.toLocaleString()} ({app.percentage.toFixed(1)}%)
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* App Usage Per Hour Stacked Chart */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <div className="flex items-center space-x-3 mb-6">
          <BarChart3 className="w-6 h-6 text-gray-700" />
          <h3 className="text-xl font-bold text-gray-900">App Usage Per Hour</h3>
        </div>

        <div className="mb-4 flex flex-wrap gap-2">
          {topApps.map((app, index) => (
            <div key={app} className="flex items-center space-x-1 text-xs">
              <div 
                className="w-3 h-3 rounded"
                style={{ backgroundColor: colors[index % colors.length] }}
              ></div>
              <span>{app}</span>
            </div>
          ))}
        </div>

        <div className="space-y-2">
          {appUsagePerHour.filter(h => Object.values(h.apps).some(v => v > 0)).map((hourData, index) => {
            const total = Object.values(hourData.apps).reduce((sum, val) => sum + val, 0);
            return (
              <div key={index} className="flex items-center space-x-3">
                <div className="w-12 text-sm text-gray-600 text-right">
                  {hourData.hour}:00
                </div>
                <div className="flex-1">
                  <div className="flex rounded-lg overflow-hidden h-6 bg-gray-100">
                    {topApps.map((app, appIndex) => {
                      const value = hourData.apps[app] || 0;
                      const percentage = total > 0 ? (value / total) * 100 : 0;
                      return (
                        <div
                          key={app}
                          className="flex items-center justify-center text-xs text-white font-medium"
                          style={{ 
                            backgroundColor: colors[appIndex % colors.length],
                            width: `${percentage}%` 
                          }}
                          title={`${app}: ${value} events`}
                        >
                          {value > 0 && percentage > 10 && value}
                        </div>
                      );
                    })}
                  </div>
                </div>
                <div className="text-sm text-gray-600 w-12 text-right">
                  {total}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}