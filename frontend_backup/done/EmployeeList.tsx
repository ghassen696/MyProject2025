import { EmployeeSummary } from '../../types/Employee-kpi';
import { User, Activity, Clock, Keyboard, TrendingUp } from 'lucide-react';
import { formatTimestamp, getStatusColor } from '../../utils/DataTransformater';

interface Props {
  employees: EmployeeSummary[];
  selectedEmployee: string;
  onEmployeeSelect: (employeeId: string) => void;
  showAll: boolean;
  onToggleShowAll: () => void;
}

export default function EmployeeList({
  employees,
  selectedEmployee,
  onEmployeeSelect,
  showAll,
  onToggleShowAll,
}: Props) {
  const sortedEmployees = [...employees].sort((a, b) => b.productivity_score - a.productivity_score);

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-gray-900">Employee Activities</h3>
        <div className="flex items-center space-x-4">
          <button
            onClick={onToggleShowAll}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              showAll 
                ? 'bg-blue-100 text-blue-700 hover:bg-blue-200' 
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            {showAll ? 'Show Individual' : 'Show All'}
          </button>
          <div className="text-sm text-gray-500">
            {employees.length} employees
          </div>
        </div>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto">
        {sortedEmployees.map((employee) => (
          <div
            key={employee.employee_id}
            onClick={() => onEmployeeSelect(employee.employee_id)}
            className={`p-4 rounded-lg border-2 cursor-pointer transition-all duration-200 hover:shadow-md ${
              selectedEmployee === employee.employee_id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-100 hover:border-gray-200'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex items-center justify-center w-10 h-10 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full">
                  <User className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h4 className="font-semibold text-gray-900">{employee.employee_id}</h4>
                  <div className="flex items-center space-x-2 mt-1">
                    <Activity className="w-3 h-3 text-gray-500" />
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(employee.status)}`}>
                      {employee.status.charAt(0).toUpperCase() + employee.status.slice(1)}
                    </span>
                  </div>
                </div>
              </div>
              
              <div className="text-right">
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center space-x-1">
                    <Keyboard className="w-4 h-4 text-blue-500" />
                    <span className="font-medium">{employee.keystrokes.toLocaleString()}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="w-4 h-4 text-green-500" />
                    <span className="font-medium">{employee.active_minutes}m</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <TrendingUp className="w-4 h-4 text-purple-500" />
                    <span className="font-medium">{employee.productivity_score}%</span>
                  </div>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Last: {formatTimestamp(employee.last_activity)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
