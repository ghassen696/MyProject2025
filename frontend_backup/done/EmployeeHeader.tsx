import { User, Clock, Activity } from "lucide-react";
import { EmployeeKPI } from "../../types/kpi";
import { formatTimestamp, getStatusColor } from "../../utils/DataTransformater";

interface Props {
  employee: EmployeeKPI;
}

export default function EmployeeHeader({ employee }: Props) {
  if (!employee) return <div>Loading...</div>;

  const productivity_score = Math.round(((employee.keystrokes_today ?? 0) / 2000) * 100);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full shadow-lg">
            <User className="w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Employee: {employee.employee_id}
            </h1>
            <div className="flex items-center space-x-2 mt-1">
              <Activity className="w-4 h-4 text-gray-500" />
              <span
                className={`px-4 py-2 rounded-full text-sm font-medium ${getStatusColor(
                  employee.employee_status
                )}`}
              >
                {
                //employee.employee_status.charAt(0).toUpperCase() + employee.employee_status.slice(1)
                employee.employee_status}
              </span>
              <div className="ml-4 px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-medium">
                {productivity_score}% Productivity
              </div>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className="flex items-center space-x-2 text-sm text-gray-600 mb-2">
            <Clock className="w-4 h-4" />
            <span>Last Activity</span>
          </div>
          <p className="text-xl font-bold text-gray-900">
            {formatTimestamp(employee.last_event_time)}
          </p>
        </div>
      </div>
    </div>
  );
}
