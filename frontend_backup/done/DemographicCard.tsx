import { EmployeeKPI } from "../../types/kpi";

interface Props {
  employee: EmployeeKPI; // passed from dashboard
}

export default function DemographicCard({ employee }: Props) {
  return (
    <div className="bg-white shadow rounded-xl p-4">
      <h2 className="text-lg font-semibold mb-4">Employee Details</h2>
      <ul className="space-y-2 text-sm">
        <li><span className="font-medium">Employee:</span> {employee.employee_id}</li>
        <li><span className="font-medium">Status:</span> {employee.employee_status}</li>
        <li><span className="font-medium">Keystrokes:</span> {employee.keystrokes_today ?? 0}</li>
        <li><span className="font-medium">Idle:</span> {Math.round((employee.total_idle_today ?? 0)/60)} mins</li>
        <li><span className="font-medium">Pauses:</span> {employee.total_pause_minutes_today ?? 0} mins</li>
      </ul>
    </div>
  );
}
