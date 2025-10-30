import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "../ui/table";
import Badge from "../ui/badge/Badge";

export interface ActivityLog {
  timestamp: number;
  event: string;
  window?: string;
  application?: string;
  control?: string;
  text?: string;
  shortcut_name?: string;
  reason?: string;
  duration_minutes?: number;
}

interface Props {
  logs: ActivityLog[];
}

export default function ActivityLogsTable({ logs }: Props) {
  const formatTimestamp = (ts: number) =>
    new Date(ts).toUTCString();

  if (!logs || logs.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 text-gray-500 dark:text-gray-400 text-center">
        No activity logs for today.
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/[0.05] bg-white dark:bg-white/[0.03] shadow-sm">
      <div className="max-w-full overflow-x-auto">
        <Table>
          {/* Header */}
          <TableHeader className="border-b border-gray-100 dark:border-white/[0.05] bg-gray-50 dark:bg-gray-800">
            <TableRow>
              <TableCell
                isHeader
                className="px-5 py-3 font-semibold text-gray-600 dark:text-gray-300 text-start text-sm"
              >
                Time
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-semibold text-gray-600 dark:text-gray-300 text-start text-sm"
              >
                Event
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-semibold text-gray-600 dark:text-gray-300 text-start text-sm"
              >
                Application
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-semibold text-gray-600 dark:text-gray-300 text-start text-sm"
              >
                Window / Control
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-semibold text-gray-600 dark:text-gray-300 text-start text-sm"
              >
                Duration
              </TableCell>
              <TableCell
                isHeader
                className="px-5 py-3 font-semibold text-gray-600 dark:text-gray-300 text-start text-sm"
              >
                Details
              </TableCell>
            </TableRow>
          </TableHeader>

          {/* Body */}
          <TableBody className="divide-y divide-gray-100 dark:divide-white/[0.05]">
            {logs.map((log, idx) => (
              <TableRow
                key={idx}
                className="hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                <TableCell className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 whitespace-nowrap">
                  {formatTimestamp(log.timestamp)}
                </TableCell>

                <TableCell className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300">
                  <Badge
                    size="sm"
                    color={
                      log.event.includes("keystroke")
                        ? "success"
                        : log.event.includes("idle")
                        ? "warning"
                        : log.event.includes("pause")
                        ? "error"
                        : "primary"
                    }
                  >
                    {log.event}
                  </Badge>
                </TableCell>

                <TableCell className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 truncate max-w-[150px]">
                  <span title={log.application || "-"}>
                    {log.application || "-"}
                  </span>
                </TableCell>

                <TableCell className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 truncate max-w-[150px]">
                  <span title={log.window || log.control || "-"}>
                    {log.window || log.control || "-"}
                  </span>
                </TableCell>

                <TableCell className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300">
                  {log.duration_minutes ? `${log.duration_minutes} min` : "-"}
                </TableCell>

                <TableCell className="px-5 py-4 text-sm text-gray-700 dark:text-gray-300 truncate max-w-[250px]">
                  <span title={log.text || log.shortcut_name || log.reason || "-"}>
                    {log.text || log.shortcut_name || log.reason || "-"}
                  </span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
