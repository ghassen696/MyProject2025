import { Search, Filter } from "lucide-react";

interface EmployeeFilterProps {
  selectedEmployee: string;
  onEmployeeSelect: (employeeId: string) => void;
  employees: string[]; // passed from dashboard
}

export default function EmployeeFilter({
  selectedEmployee,
  onEmployeeSelect,
  employees,
}: EmployeeFilterProps) {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <div className="flex items-center space-x-2">
          <Filter className="w-5 h-5 text-gray-500" />
          <h3 className="text-sm font-medium text-gray-900">Filter Employee</h3>
        </div>

        <div className="flex-1 max-w-sm">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <select
              value={selectedEmployee}
              onChange={(e) => onEmployeeSelect(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">All Employees</option>
              {employees.map((employeeId) => (
                <option key={employeeId} value={employeeId}>
                  {employeeId}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="text-sm text-gray-500">
          {selectedEmployee
            ? `Viewing: ${selectedEmployee}`
            : `${employees.length} employees total`}
        </div>
      </div>
    </div>
  );
}
