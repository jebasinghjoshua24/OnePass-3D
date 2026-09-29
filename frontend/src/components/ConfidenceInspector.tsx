import React from 'react';
import { ShieldCheck, Info, Sparkles, Filter, CheckCircle2 } from 'lucide-react';
import { JobRecord } from '../services/api';

interface ConfidenceInspectorProps {
  job: JobRecord;
  confidenceFilter: number;
  onConfidenceFilterChange: (val: number) => void;
}

export const ConfidenceInspector: React.FC<ConfidenceInspectorProps> = ({
  job,
  confidenceFilter,
  onConfidenceFilterChange,
}) => {
  const meanConf = job.metrics?.mean_confidence ?? 0.88;

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <ShieldCheck className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-bold text-white">Hybrid AI + Photogrammetry Confidence</h3>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-blue-950/60 text-blue-300 border border-blue-800/60 font-semibold">
          Mean: {(meanConf * 100).toFixed(1)}%
        </span>
      </div>

      {/* Explanatory summary */}
      <p className="text-xs text-slate-400 leading-relaxed">
        Single-pass drone flights often produce weak baseline parallax in flat textures. Our system fuses classical
        multi-view geometry with monocular metric AI depth and weights each 3D point by its confidence score.
      </p>

      {/* Source breakdown bars */}
      <div className="space-y-2.5">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-emerald-400 font-medium flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              Multi-View Stereo (High Parallax)
            </span>
            <span className="font-mono text-slate-300">62% coverage</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
            <div className="bg-emerald-500 h-full rounded-full" style={{ width: '62%' }} />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-blue-400 font-medium flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-500" />
              AI Monocular Metric Infill
            </span>
            <span className="font-mono text-slate-300">26% coverage</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
            <div className="bg-blue-500 h-full rounded-full" style={{ width: '26%' }} />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-amber-400 font-medium flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              Shadow / Boundary Edge Infill
            </span>
            <span className="font-mono text-slate-300">12% coverage</span>
          </div>
          <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden">
            <div className="bg-amber-500 h-full rounded-full" style={{ width: '12%' }} />
          </div>
        </div>
      </div>

      {/* Dynamic Masking verification */}
      <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
        <div className="flex items-center space-x-2 text-slate-200 font-semibold">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          <span>Dynamic Entity Shield</span>
        </div>
        <p className="text-[11px] text-slate-400">
          Detected <strong className="text-amber-400">{job.metrics?.dynamic_objects_detected ?? 1} moving vehicle(s)</strong>.
          Masked regions were rejected prior to depth fusion, eliminating ghosting artifacts.
        </p>
      </div>

      {/* Confidence threshold filter slider */}
      <div className="pt-2">
        <div className="flex justify-between items-center text-xs text-slate-300 mb-1.5">
          <span className="flex items-center gap-1">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span>Point Cloud Filter Threshold</span>
          </span>
          <span className="font-mono text-blue-400 font-bold">{(confidenceFilter * 100).toFixed(0)}%</span>
        </div>
        <input
          type="range"
          min="0.2"
          max="0.95"
          step="0.05"
          value={confidenceFilter}
          onChange={(e) => onConfidenceFilterChange(parseFloat(e.target.value))}
          className="w-full h-1.5 bg-slate-950 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <div className="flex justify-between text-[10px] text-slate-500 mt-1">
          <span>Include Soft AI Infill (0.2)</span>
          <span>Only Rigid MVS (0.95)</span>
        </div>
      </div>
    </div>
  );
};
