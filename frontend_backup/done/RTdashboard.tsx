import React, { useEffect, useState, useRef } from "react";
import PageMeta from "../../components/common/PageMeta";
import EmployeeHeader from "../../components/KPI/EmployeeHeader";
import KPICards from "../../components/KPI/KPICards";
import EventTimeline from "../../components/KPI/EventTimeLine";
import EventDistributionChart from "../../components/KPI/EventDistributionChart";
import ActivityLogsTable from "../../components/KPI/ActivityChart";
import HourlyKeystrokesChart from "../../components/KPI/HourlyKeystrokesChart";
import EventFrequencyHeatmap from "../../components/KPI/EventFrequencyHeatMap";
import KeystrokesVsIdleChart from "../../components/KPI/KeystrokesVsIdleChart";
import EmployeeList from "../../components/KPI/EmployeeList";
import EmployeeFilter from "../../components/KPI/EmployeeFilter";

import { ActivityLog, ProcessedEmployeeData } from "../../types/Employee-kpi";
import { EmployeeKPI } from "../../types/kpi";
import { 
  transformElasticsearchData, 
  generateEmployeeSummaries,
  getEventTypeCounts,
  generateHourlyKeystrokes
} from "../../utils/DataTransformater";

export default function Dashboard() {
  const [dataMap, setDataMap] = useState<Record<string, ProcessedEmployeeData>>({});
  const [selectedEmployee, setSelectedEmployee] = useState<string>("all");
  const [loading, setLoading] = useState(true);

  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityPageSize] = useState(20);
  const [loadingActivity, setLoadingActivity] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const lastEmployeeId = useRef<string | null>(null);
  const firstLoad = useRef(true);

  const latestTimestampRef = useRef<number | null>(null);

  const transformData = (data: EmployeeKPI[]): ProcessedEmployeeData[] =>
    data.map(emp => ({
      employee_id: emp.employee_id,
      total_keystrokes: emp.keystrokes_today,
      total_idle_minutes: emp.total_idle_today / 60,
      total_pauses: emp.pauses_today,
      total_pause_minutes: emp.total_pause_minutes_today,
      keystrokes_per_minute: emp.keystrokes_per_minute,
      active_minutes: emp.active_minutes,
      events_today: emp.events_today,
      employee_status: emp.employee_status,
      doc_id: emp.doc_id,
      last_idle_duration: emp.last_idle_duration,
      last_event_time: emp.last_event_time,
      productivity_score: emp.productivity_score ?? 0,
    }));

  // ------------------------
  // Fetch KPI
  // ------------------------
  const fetchKPI = async () => {
    try {
      const res = await fetch("http://localhost:8000/kpi/", { cache: "no-store" });
      if (!res.ok) throw new Error("Failed to fetch KPI data");
      const jsonData: EmployeeKPI[] = await res.json();
      const transformedData = transformData(jsonData);

      setDataMap(() => {
        const newMap: Record<string, ProcessedEmployeeData> = {};
        transformedData.forEach(emp => {
          newMap[emp.employee_id] = emp;
        });
        return newMap;
      });
    } catch (err) {
      console.error("Error fetching KPI:", err);
    } finally {
      if (firstLoad.current) {
        setLoading(false);
        firstLoad.current = false;
      }
    }
  };

  // ------------------------
  // Fetch new activity logs
  // ------------------------
  const fetchNewActivityLogs = async (employeeId: string) => {
    try {
      const params = new URLSearchParams({ employee_id: employeeId });
      if (latestTimestampRef.current) {
        params.append("start_ts", (latestTimestampRef.current + 1).toString());
      }

      const res = await fetch(`http://localhost:8000/raw_activity/?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to fetch activity logs");
      const data = await res.json();

      if (data.events.length > 0) {
        const container = scrollRef.current;
        const isNearBottom = container
          ? container.scrollHeight - container.scrollTop - container.clientHeight < 50
          : true;

        setActivityLogs(prevLogs => [...prevLogs, ...data.events]);
        latestTimestampRef.current = data.events[data.events.length - 1].timestamp;
        setActivityTotal(prev => prev + data.events.length);

        // Auto-scroll if user was near the bottom
        if (container && isNearBottom) {
          setTimeout(() => {
            container.scrollTop = container.scrollHeight;
          }, 0);
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const allEmployees = Object.values(dataMap);
  const currentEmployee = selectedEmployee !== "all" ? dataMap[selectedEmployee] || null : null;

  // ------------------------
  // Load activity logs when employee changes
  // ------------------------
  useEffect(() => {
  if (!currentEmployee) return;

  // Reset on employee change
  setActivityLogs([]);
  setActivityTotal(0);
  latestTimestampRef.current = null;

  const fetchInitialLogs = async () => {
    try {
      setLoadingActivity(true);
      const res = await fetch(
        `http://localhost:8000/raw_activity/?employee_id=${currentEmployee.employee_id}&from_=0&size=1000`
      );
      const data = await res.json();
      if (!res.ok) throw new Error("Failed to fetch activity logs");

      setActivityLogs(data.events);
      setActivityTotal(data.total);

      if (data.events.length > 0) {
        latestTimestampRef.current = data.events[data.events.length - 1].timestamp;
        // Scroll to bottom only on first load
        setTimeout(() => {
          scrollRef.current!.scrollTop = scrollRef.current!.scrollHeight;
        }, 0);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingActivity(false);
    }
  };

  fetchInitialLogs();

  const interval = setInterval(() => {
    const fetchNewLogs = async () => {
      try {
        const params = new URLSearchParams({ employee_id: currentEmployee.employee_id });
        if (latestTimestampRef.current)
          params.append("start_ts", (latestTimestampRef.current + 1).toString());

        const res = await fetch(`http://localhost:8000/raw_activity/?${params.toString()}`);
        const data = await res.json();

        if (data.events.length > 0) {
          const container = scrollRef.current;
          const isNearBottom = container
            ? container.scrollHeight - container.scrollTop - container.clientHeight < 50
            : true;

          // Append instead of replacing
          setActivityLogs(prevLogs => [...prevLogs, ...data.events]);
          latestTimestampRef.current = data.events[data.events.length - 1].timestamp;
          setActivityTotal(prev => prev + data.events.length);

          if (container && isNearBottom) {
            setTimeout(() => {
              container.scrollTop = container.scrollHeight;
            }, 0);
          }
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchNewLogs();
  }, 10000);

  return () => clearInterval(interval);
}, [currentEmployee]);

  // ------------------------
  // Refresh KPI every 10s
  // ------------------------
  useEffect(() => {
    fetchKPI();
    const interval = setInterval(fetchKPI, 10000);
    return () => clearInterval(interval);
  }, []);

  const employeeSummaries = generateEmployeeSummaries(allEmployees);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <>
      <PageMeta title="Employee KPI Dashboard" description="Real-time employee productivity and activity monitoring dashboard" />
      <div className="space-y-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-6 text-white">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold mb-2">Employee KPI Dashboard</h1>
              <p className="text-blue-100">Real-time productivity monitoring and analytics</p>
            </div>
            <EmployeeFilter
              employees={allEmployees.map(emp => emp.employee_id)}
              selectedEmployee={selectedEmployee}
              onEmployeeSelect={setSelectedEmployee}
            />
          </div>
        </div>

        {/* Employee Header */}
        {currentEmployee && <EmployeeHeader employee={currentEmployee} />}

        {/* KPI Cards */}
        {currentEmployee && <KPICards employee={currentEmployee} />}

        {/* Main Content */}
        {currentEmployee ? (
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            <div className="xl:col-span-15 space-y-6">
              {/* Row 1 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <EventDistributionChart eventCounts={getEventTypeCounts(currentEmployee.events_today)} />
                <EventTimeline events={currentEmployee.events_today} />
                <KeystrokesVsIdleChart employee={currentEmployee} />
              </div>

              {/* Row 2 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <EventFrequencyHeatmap events={currentEmployee.events_today || []} />
                <HourlyKeystrokesChart data={generateHourlyKeystrokes(currentEmployee.total_keystrokes, currentEmployee.events_today)} />
              </div>

              {/* Activity Logs */}
              <div className="mt-6 relative">
                {loadingActivity && (
                  <div className="absolute inset-0 bg-white/50 dark:bg-gray-900/50 flex justify-center items-center rounded-xl z-10">
                    <div className="animate-spin h-8 w-8 border-b-2 border-blue-600 rounded-full"></div>
                  </div>
                )}
                <div ref={scrollRef} className="max-h-[400px] overflow-y-auto border rounded-xl">
                  <ActivityLogsTable logs={activityLogs} />
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6">
            <EmployeeList
              employees={employeeSummaries}
              selectedEmployee={selectedEmployee}
              onEmployeeSelect={setSelectedEmployee}
            />
          </div>
        )}
      </div>
    </>
  );
}
