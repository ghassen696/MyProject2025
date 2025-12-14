import { useEffect, useState } from "react";
import PageBreadcrumb from "../components/common/PageBreadCrumb";
import PageMeta from "../components/common/PageMeta";

// Types
interface Request {
  _id: string; // Elasticsearch document ID
  employee_id: string;
  request_type: string;
  start_ts?: number;
  end_ts?: number;
  reason: string;
  requested_at: number;
  status: "pending" | "approved" | "declined";
  activities?: Activity[];
}

interface Activity {
  timestamp: string;
  event: string;
  application: string;
  control: string;
}

export default function Requests() {
  const [requests, setRequests] = useState<Request[]>([]);
  const [loading, setLoading] = useState(false);
  const [employeeFilter, setEmployeeFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState<string[]>([]);

  // Fetch requests from backend
  const fetchRequests = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (employeeFilter) params.append("employee_id", employeeFilter);
      if (typeFilter.length > 0) typeFilter.forEach(t => params.append("type", t));
      params.append("from_", "0");
      params.append("size", "100"); // adjust as needed

      const res = await fetch(`http://localhost:8000/admin/requests?${params.toString()}`);
      const data = await res.json();
      
      // Map Elasticsearch _id
      const mapped = data.requests.map((r: any) => ({ ...r, _id: r._id || r.id }));
      setRequests(mapped);
    } catch (err) {
      console.error("Error fetching requests:", err);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  // Derive available request types
  const requestTypes = Array.from(new Set(requests.map((r) => r.request_type)));

  // Filter pending requests by employee/type
  const filtered = requests.filter((r) => {
    const matchesEmployee = !employeeFilter || r.employee_id.includes(employeeFilter);
    const matchesType = typeFilter.length === 0 || typeFilter.includes(r.request_type);
    return matchesEmployee && matchesType && r.status === "pending";
  });

  // Approve or decline request
  const handleDecision = async (_id: string, decision: "approved" | "declined") => {
    try {
      const res = await fetch(`http://localhost:8000/admin/requests/${_id}/decision?decision=${decision}`, {
        method: "POST",
      });
      if (!res.ok) throw new Error("Failed to update request");
      setRequests(prev =>
        prev.map(r => (r._id === _id ? { ...r, status: decision } : r))
      );
    } catch (err) {
      console.error("Error updating request:", err);
      alert("Failed to update request");
    }
  };

  return (
    <div>
      <PageMeta title="Requests | Dashboard" description="Manage employee modification requests." />
      <PageBreadcrumb pageTitle="🛠️ Employee Modification Requests" />

      <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-5 py-7 dark:border-gray-800 dark:bg-white/[0.03] xl:px-10 xl:py-12">
        <div className="mx-auto max-w-5xl">
          {/* Filters */}
          <div className="mb-6 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-600">Filter by Employee ID</label>
              <input
                type="text"
                value={employeeFilter}
                onChange={(e) => setEmployeeFilter(e.target.value)}
                placeholder="Enter employee ID"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600">Request Type</label>
              <select
                multiple
                value={typeFilter}
                onChange={(e) =>
                  setTypeFilter(Array.from(e.target.selectedOptions, (opt) => opt.value))
                }
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm"
              >
                {requestTypes.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          </div>

          <h3 className="text-lg font-semibold mb-4">
            Pending Requests ({filtered.length})
          </h3>

          {loading && <p>Loading requests...</p>}
          {!loading && filtered.length === 0 && <p className="text-gray-500">No pending modification requests.</p>}

          <div className="space-y-4">
            {filtered.map((req) => (
              <details key={req._id} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <summary className="cursor-pointer font-medium">
                  Employee: {req.employee_id} | Type: {req.request_type}
                </summary>
                <div className="mt-2 space-y-2 text-sm text-gray-700">
                  <p><strong>Requested at:</strong> {new Date(req.requested_at).toLocaleString()}</p>
                  <p>
                    <strong>Time Interval:</strong>{" "}
                    {req.start_ts ? new Date(req.start_ts).toLocaleString() : "-"} →{" "}
                    {req.end_ts ? new Date(req.end_ts).toLocaleString() : "-"}
                  </p>
                  <p><strong>Reason:</strong> {req.reason}</p>

                  {/* Activities if any */}
                  {req.activities && req.activities.length > 0 ? (
                    <div className="overflow-x-auto mt-3">
                      <table className="min-w-full border border-gray-200 text-sm">
                        <thead className="bg-gray-100">
                          <tr>
                            <th className="border px-3 py-2 text-left">Timestamp</th>
                            <th className="border px-3 py-2 text-left">Event</th>
                            <th className="border px-3 py-2 text-left">Application</th>
                            <th className="border px-3 py-2 text-left">Control</th>
                          </tr>
                        </thead>
                        <tbody>
                          {req.activities.map((a, i) => (
                            <tr key={i}>
                              <td className="border px-3 py-2">{new Date(a.timestamp).toLocaleString()}</td>
                              <td className="border px-3 py-2">{a.event}</td>
                              <td className="border px-3 py-2">{a.application}</td>
                              <td className="border px-3 py-2">{a.control}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                  )}

                  {/* Actions */}
                  <div className="mt-4 flex space-x-4">
                    <button
                      onClick={() => handleDecision(req._id, "approved")}
                      className="rounded-lg bg-green-600 px-4 py-2 text-white hover:bg-green-700"
                    >
                      ✅ Approve
                    </button>
                    <button
                      onClick={() => handleDecision(req._id, "declined")}
                      className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700"
                    >
                      ❌ Decline
                    </button>
                  </div>
                </div>
              </details>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
