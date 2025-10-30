import { EmployeeKPI } from "../../types/kpi";

interface Props {
  employee: EmployeeKPI;
}

export default function EmployeeMetrics({ employee }: Props) {
  const metrics = [
    { label: "Employee", value: employee.employee_id },
    { label: "Keystrokes / min", value: employee.keystrokes_per_minute.toFixed(2) },
    { label: "Active Minutes", value: employee.active_minutes.toFixed(1) },
    { label: "Pause Minutes", value: employee.total_pause_minutes_today?.toFixed(2) ?? 0 },
    { label: "Status", value: employee.employee_status },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      {metrics.map(m => (
        <div key={m.label} className="bg-white rounded-xl shadow p-4 flex flex-col items-center justify-center">
          <p className="text-sm text-gray-500">{m.label}</p>
          <p className="text-lg font-semibold">{m.value}</p>
        </div>
      ))}
    </div>
  );
}
