import React from 'react';
import { Compass, Navigation, ArrowUpRight, Globe, Gauge } from 'lucide-react';
import { JobRecord } from '../services/api';

interface TelemetryPanelProps {
  job: JobRecord;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({ job }) => {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Navigation className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-bold text-white">Flight Telemetry & Trajectory Profile</h3>
        </div>
        <span className="text-[11px] text-emerald-400 font-mono">Synced to Video Timestamps</span>
      </div>

      {/* Primary Flight Parameters */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
          <span className="text-slate-500 block text-[10px] uppercase">Reference GPS</span>
          <span className="font-mono text-white font-semibold block mt-0.5">28.6139° N</span>
          <span className="font-mono text-slate-400 text-[11px]">77.2090° E</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
          <span className="text-slate-500 block text-[10px] uppercase">Flight Altitude</span>
          <span className="font-mono text-emerald-400 font-semibold block mt-0.5 text-sm">120.5 m AGL</span>
          <span className="font-mono text-slate-400 text-[11px]">Baro Alt: 120.3 m</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
          <span className="text-slate-500 block text-[10px] uppercase">Gimbal Pitch</span>
          <span className="font-mono text-sky-400 font-semibold block mt-0.5 text-sm">-45.0° Oblique</span>
          <span className="font-mono text-slate-400 text-[11px]">Roll: 0.1°</span>
        </div>
        <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs">
          <span className="text-slate-500 block text-[10px] uppercase">Survey Pass</span>
          <span className="font-mono text-amber-400 font-semibold block mt-0.5 text-sm">Single-Pass</span>
          <span className="font-mono text-slate-400 text-[11px]">Radius: 35m Orbit</span>
        </div>
      </div>

      {/* Altitude Graph Visualization */}
      <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
        <div className="flex justify-between items-center text-xs text-slate-400">
          <span>Flight Altitude Profile (m) over time</span>
          <span className="text-[10px] font-mono text-slate-500">Duration: 24.5s</span>
        </div>
        <div className="h-16 flex items-end gap-1.5 pt-2">
          {[120, 120.5, 120.8, 121.2, 121.5, 121.8, 122.1, 122.3, 122.5, 122.6, 122.7, 122.8, 122.9, 123.0, 123.1, 123.2, 123.2, 123.3, 123.4, 123.5].map((val, idx) => {
            const heightPercent = ((val - 119) / 5.5) * 100;
            return (
              <div
                key={idx}
                className="flex-1 bg-gradient-to-t from-emerald-600/40 to-teal-400 rounded-t-sm hover:bg-emerald-400 transition-colors cursor-pointer group relative"
                style={{ height: `${heightPercent}%` }}
              >
                <div className="hidden group-hover:block absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-slate-800 px-1.5 py-0.5 rounded text-[9px] font-mono text-white whitespace-nowrap z-10 border border-slate-700">
                  {val.toFixed(1)}m
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-[10px] font-mono text-slate-500 pt-1">
          <span>0.0s (Start)</span>
          <span>12.0s (Mid-Pass)</span>
          <span>24.5s (End)</span>
        </div>
      </div>
    </div>
  );
};
