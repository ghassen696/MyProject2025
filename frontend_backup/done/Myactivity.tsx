// pages/MyActivity.tsx
import { useState, useEffect } from "react";
import axios from "axios";

export default function MyActivity() {
  const [logs, setLogs] = useState<any[]>([]);
  const [idleIntervals, setIdleIntervals] = useState<any[]>([]);
  const [requests, setRequests] = useState<any[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(
    new Date().toISOString().substring(0, 10)
  );

  const [selectedInterval, setSelectedInterval] = useState("");
  const [pauseType, setPauseType] = useState("lunch");
  const [reason, setReason] = useState("");

  const [page, setPage] = useState(1);
  const [totalLogs, setTotalLogs] = useState(0);
  const pageSize = 20; // logs per page

  const EMPLOYEE_ID = "G50047910-5JjP5"; // Replace with actual session/user ID

  // ----------------- Fetch Data ----------------- //
  const fetchData = async (pageNumber = 1) => {
    try {
      // Start and end timestamps for the selected date
      const start = new Date(`${selectedDate}T00:00:00`).getTime();
      const end = new Date(`${selectedDate}T23:59:59`).getTime();

      // Fetch activity logs with pagination
      const logsRes = await axios.get("http://localhost:8000/raw_activity/", {
        params: {
          employee_id: EMPLOYEE_ID,
          start_ts: start,
          end_ts: end,
          page: pageNumber,
          page_size: pageSize,
        },
      });

      const data = logsRes.data;
      setLogs(data.events);
      setPage(data.page);
      setTotalLogs(data.total);

      // ---------------- Extract Idle Intervals ---------------- //
      const idleStarts = data.events.filter((e: any) => e.event === "idle_start");
      const idleEnds = data.events.filter((e: any) => e.event === "idle_end");

      const intervals = idleStarts.map((startEvent: any) => {
        // Find the corresponding idle_end event
        const endEvent = idleEnds.find(
          (e: any) =>
            e.session_id === startEvent.session_id &&
            e.timestamp > startEvent.timestamp
        );

        if (!endEvent) return null;

        return {
          id: endEvent.idle_id, // ✅ must use idle_end's idle_id
          start: new Date(startEvent.timestamp).toLocaleTimeString(),
          end: new Date(endEvent.timestamp).toLocaleTimeString(),
          duration: `${Math.round((endEvent.timestamp - startEvent.timestamp) / 60000)} min`,
        };
      }).filter(Boolean);

      setIdleIntervals(intervals);

      // ---------------- Fetch Requests ---------------- //
      const reqRes = await axios.get(
        `http://localhost:8000/requests/employee/${EMPLOYEE_ID}`,
        {
          params: { status: "pending" },
        }
      );
      console.log("Requests API response:", reqRes.data);

      setRequests(reqRes.data.requests);
    } catch (err) {
      console.error(err);
      alert("Error fetching data from backend");
    }
  };

  useEffect(() => {
    fetchData(1);
  }, [selectedDate]);

  // ----------------- Submit Idle Correction ----------------- //
  const handleCorrectionSubmit = async () => {
    if (!selectedInterval) {
      alert("Please select an idle interval first.");
      return;
    }

    try {
      const res = await axios.post("http://localhost:8000/requests/idle", {
        employee_id: EMPLOYEE_ID,
        idle_id: selectedInterval, // ✅ comes from idle_end
        requested_pause_type: pauseType,
        reason,
      });

      alert(
        `Correction submitted! Effective duration: ${res.data.effective_duration_sec} sec`
      );

      // Refresh requests
      fetchData(page);
      setReason("");
      setSelectedInterval("");
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to submit correction");
    }
  };

  // ----------------- Submit Day Exclusion ----------------- //
  const handleExcludeDay = async () => {
    try {
      await axios.post("http://localhost:8000/requests/day_exclusion", {
        employee_id: EMPLOYEE_ID,
        date: selectedDate,
        reason: "Session issues / Keylogger problem",
      });

      alert(`Exclude request for ${selectedDate} submitted.`);

      fetchData(page);
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || "Failed to submit exclusion");
    }
  };

  // ----------------- Pagination ----------------- //
  const handlePrevPage = () => {
    if (page > 1) fetchData(page - 1);
  };
  const handleNextPage = () => {
    if (page * pageSize < totalLogs) fetchData(page + 1);
  };

  // ----------------- Render ----------------- //
  return (
    <div className="min-h-screen rounded-2xl border border-gray-200 bg-white px-6 py-8 dark:border-gray-800 dark:bg-white/[0.03]">
      <div className="mx-auto w-full max-w-6xl">
        <h2 className="mb-6 text-2xl font-semibold text-gray-800 dark:text-white/90">
          👤 My Activity & Data Correction
        </h2>

        {/* Date Picker */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Day
          </label>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          />
        </div>

        {/* Logs Table */}
        <div className="mb-8">
          <h3 className="mb-3 text-lg font-medium text-gray-800">📋 Activity Logs</h3>
          {logs.length === 0 ? (
            <p className="text-gray-500">No logs found.</p>
          ) : (
            <>
              <div className="overflow-x-auto rounded-lg border">
                <table className="min-w-full text-sm">
                  <thead className="bg-gray-100 text-left">
                    <tr>
                      <th className="px-4 py-2">Timestamp</th>
                      <th className="px-4 py-2">Event</th>
                      <th className="px-4 py-2">Application</th>
                      <th className="px-4 py-2">Text</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map((log, idx) => (
                      <tr key={idx} className="border-t">
                        <td className="px-4 py-2">
                          {new Date(log.timestamp).toLocaleTimeString()}
                        </td>
                        <td className="px-4 py-2">{log.event}</td>
                        <td className="px-4 py-2">{log.application || ""}</td>
                        <td className="px-4 py-2">{log.text || ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex justify-between mt-4">
                <button
                  disabled={page === 1}
                  onClick={handlePrevPage}
                  className="rounded bg-gray-200 px-4 py-2 disabled:opacity-50"
                >
                  Previous
                </button>
                <span>
                  Page {page} of {Math.ceil(totalLogs / pageSize)}
                </span>
                <button
                  disabled={page * pageSize >= totalLogs}
                  onClick={handleNextPage}
                  className="rounded bg-gray-200 px-4 py-2 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>

        {/* Idle Intervals */}
        <div className="mb-8">
          <h3 className="mb-3 text-lg font-medium text-gray-800">🕵️ Detected Idle Intervals</h3>
          {idleIntervals.length === 0 ? (
            <p className="text-gray-500">No idle intervals detected.</p>
          ) : (
            <ul className="space-y-2">
              {idleIntervals.map((itv) => (
                <li
                  key={itv.id}
                  className="rounded-md border p-3 text-sm text-gray-700 bg-gray-50"
                >
                  {itv.start} → {itv.end} ({itv.duration})
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Correction Form */}
        <div className="mb-8">
          <h3 className="mb-3 text-lg font-medium text-gray-800">✏️ Correct Idle as Pause</h3>
          <select
            value={selectedInterval}
            onChange={(e) => setSelectedInterval(e.target.value)}
            className="mb-3 block w-full rounded-md border px-3 py-2"
          >
            <option value="">Select Idle Interval</option>
            {idleIntervals.map((itv) => (
              <option key={itv.id} value={itv.id}>
                {itv.start} → {itv.end} ({itv.duration})
              </option>
            ))}
          </select>

          <select
            value={pauseType}
            onChange={(e) => setPauseType(e.target.value)}
            className="mb-3 block w-full rounded-md border px-3 py-2"
          >
            <option value="lunch">Lunch</option>
            <option value="bathroom">Bathroom</option>
            <option value="phone_call">Phone Call</option>
            <option value="meeting">Meeting</option>
            <option value="personal_break">Personal Break</option>
          </select>

          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Enter justification..."
            className="mb-3 block w-full rounded-md border px-3 py-2"
          />

          <button
            onClick={handleCorrectionSubmit}
            className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            Submit Correction
          </button>
        </div>

        {/* Quick Actions */}
        <div className="mb-8">
          <h3 className="mb-3 text-lg font-medium text-gray-800">🔁 Quick Actions</h3>
          <p className="text-sm text-gray-600 mb-3">
            If your session had connection issues, you can exclude this day from scoring.
          </p>
          <button
            onClick={handleExcludeDay}
            className="rounded-lg bg-red-600 px-4 py-2 text-white hover:bg-red-700"
          >
            Exclude Day
          </button>
        </div>

        {/* Requests List */}
        <div className="mb-8">
          <h3 className="mb-3 text-lg font-medium text-gray-800">📨 Your Requests</h3>
          {requests.length === 0 ? (
            <p className="text-gray-500">No requests submitted.</p>
          ) : (
            <ul className="space-y-2">
              {requests.map((req) => (
                <li
                  key={req.id}
                  className="rounded-md border p-3 text-sm bg-gray-50 flex justify-between"
                >
                  <span>
                    {req.request_type} — {req.reason}
                  </span>
                  <span className="font-medium text-gray-700">{req.status}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
