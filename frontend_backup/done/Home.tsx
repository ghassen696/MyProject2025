import React, { useEffect, useState } from 'react';
import PageMeta from '../../components/common/PageMeta';
import SummaryCards from '../../components/ProductivityAnalytics/SummaryCards';
import TypingOverTimeChart from '../../components/ProductivityAnalytics/TypingOverTimeChart';
import IdleTimeAnalysis from '../../components/ProductivityAnalytics/IdleTimeAnalysis';
import PauseAnalysis from '../../components/ProductivityAnalytics/PauseAnalysis';
import ShortcutsAnalysis from '../../components/ProductivityAnalytics/ShortcutsAnalysis';
import ApplicationUsage from '../../components/ProductivityAnalytics/ApplicationUsage';
import WindowSwitching from '../../components/ProductivityAnalytics/WindowSwitching';
import SessionOverview from '../../components/ProductivityAnalytics/SessionOverview';
import ProductivityGauge from '../../components/ProductivityAnalytics/ProductivityGauge';
import EventDiversity from '../../components/ProductivityAnalytics/EventDiversity';
import { ProductivityData } from '../../types/productivity-analytics';
import { transformPauseData } from '../../utils/DataTransformater';

export default function home() {
  const [data, setData] = useState<ProductivityData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const response = await fetch(`http://localhost:8000/api/productivity/G50047910-5JjP5/2025-10-09`);
      
      const data = await response.json();
      console.log("Raw response:", data);

      setTimeout(() => {
        setData(data);
        setLoading(false);
      }, 1000);
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">No Data Available</h2>
          <p className="text-gray-600">Unable to load productivity analytics data.</p>
        </div>
      </div>
    );
  }
   const pauseData = transformPauseData(data.pause_per_hour); 
  return (
    <>
      <PageMeta
        title="Productivity Analytics Dashboard"
        description="Comprehensive productivity analytics and insights dashboard"
      />
      
      <div className="space-y-8">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-8 text-white">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h1 className="text-4xl font-bold mb-2">Productivity Analytics</h1>
              <p className="text-indigo-100 text-lg">
                Comprehensive insights for {data.employee_id} • {data.date}
              </p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-xl p-4">
              <div className="text-2xl font-bold">{data.productivity_score.toFixed(2)}/100</div>
              <div className="text-indigo-100 text-sm">Overall Score</div>
            </div>
          </div>
        </div>

        {/* 1. Summary Cards */}
        <SummaryCards data={data} />

        {/* 2. Typing Over Time */}
        <TypingOverTimeChart 
          typingData={data.typing_per_hour} 
          keystrokesData={data.keystrokes_per_active_hour} 
        />

        {/* 3. Idle Time Analysis */}
        <IdleTimeAnalysis 
          idlePerHour={data.idle_per_hour} 
          idlePerApp={data.idle_per_app} 
        />

        {/* 4. Pause Analysis */}

        <PauseAnalysis 
          pausePerHour={pauseData}
          avgPauseDuration={data.avg_pause_duration_min}
          totalPauseMin={data.pause_total_min}
        />

        {/* 5. Shortcuts Analysis */}
        <ShortcutsAnalysis 
          shortcutsUsed={data.shortcuts_used}
          shortcutsPerHour={data.shortcuts_per_hour}
          totalShortcuts={data.shortcut_count}
        />

        {/* 6. Application Usage */}
        <ApplicationUsage 
          activePerApp={data.active_per_app}
          appUsagePerHour={data.app_usage_per_hour}
        />

        {/* 7. Window Switching */}
        <WindowSwitching 
          topWindows={data.top_windows}
          windowSwitchCount={data.window_switch_count}
          contextSwitchRate={data.context_switch_rate}
        />

        {/* 8. Session Overview */}
        <SessionOverview sessions={data.sessions} />

        {/* 9. Productivity Gauge 
        <ProductivityGauge 
          productivityScore={data.productivity_score}
          focusRatio={data.focus_ratio}
        />*/}

        {/* 10. Event Diversity */}
        <EventDiversity 
          uniqueAppsCount={data.unique_apps_count}
          donutChart={data.donut_chart}
          activeEvents={data.active_events}
        />
      </div>
    </>
  );
}