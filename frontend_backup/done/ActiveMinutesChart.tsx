import { EmployeeKPI } from "../../types/kpi";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

interface Props {
  data: EmployeeKPI[];
}

export default function ActiveMinutesChart({ data }: Props) {
  const labels = data.map(d => d.employee_id);

  const chartData = {
    labels,
    datasets: [
      {
        label: "Keystrokes",
        data: data.map(d => d.keystrokes_today.toFixed(2) ?? 0),
        backgroundColor: "#4f46e5",
      },
      {
        label: "Pause Minutes",
        data: data.map(d => d.total_pause_minutes_today.toFixed(2) ?? 0),
        backgroundColor: "#f59e0b",
      },
      {
        label: "Idle Minutes",
        data: data.map(d => (d.total_idle_today ?? 0)/60),
        backgroundColor: "#ef4444",
      },
    ],
  };

  return (
    <div className="bg-white shadow rounded-xl p-4">
      <h2 className="text-lg font-semibold mb-4">Keystrokes, Pauses & Idle Time</h2>
      <Bar data={chartData} />
    </div>
  );
}
