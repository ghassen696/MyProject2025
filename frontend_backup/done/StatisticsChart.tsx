import { EmployeeKPI } from "../../types/kpi";
import { Pie } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

interface Props {
  data: EmployeeKPI[];
}

export default function StatisticsChart({ data }: Props) {
  const counts = {
    active: data.filter(d => d.active_minutes),
    idle: data.filter(d => d.employee_status === 'idle').length,
    offline: data.filter(d => d.employee_status === 'offline').length,
  };

  const chartData = {
    labels: ['Active', 'Idle', 'Offline'],
    datasets: [
      { data: [counts.active, counts.idle, counts.offline], backgroundColor: ['#22c55e', '#eab308', '#ef4444'] }
    ]
  };

  return (
    <div className="bg-white shadow rounded-xl p-4">
      <h2 className="text-lg font-semibold mb-4">Employee Status</h2>
      <Pie data={chartData} />
    </div>
  );
}
