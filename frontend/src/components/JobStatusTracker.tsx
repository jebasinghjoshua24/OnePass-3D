import React, { useRef, useEffect } from 'react';
import { 
  CheckCircle2, Clock, Terminal, AlertTriangle, XCircle, 
  RotateCw, Camera, Eye, Zap, ShieldAlert, Compass, Box, MapPin, Download
} from 'lucide-react';
import { JobRecord } from '../services/api';

interface JobStatusTrackerProps {
  job: JobRecord;
  onCancel: (jobId: string) => void;
  onViewResults: () => void;
}

const STAGES = [
  { id: 'extracting', label: 'Extract Frames', icon: Camera },
  { id: 'sharpness_filtering', label: 'Sharpness Scoring', icon: Eye },
  { id: 'preprocessing', label: 'Denoise & CLAHE', icon: Zap },
  { id: 'masking', label: 'Dynamic Masking', icon: ShieldAlert },
  { id: 'pose_estimation', label: 'Pose Estimation', icon: Compass },
  { id: 'depth_estimation', label: 'Dense Depth (MVS+AI)', icon: Box },
  { id: 'depth_fusion', label: 'Confidence Fusion', icon: CheckCircle2 },
  { id: 'meshing', label: 'Mesh & Texturing', icon: Box },
  { id: 'georeferencing', label: 'Georeference UTM', icon: MapPin },
  { id: 'exporting', label: 'Artifact Export', icon: Download },
];

export const JobStatusTracker: React.FC<JobStatusTrackerProps> = ({ job, onCancel, onViewResults }) => {
  const logTerminalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (logTerminalRef.current) {
      logTerminalRef.current.scrollTop = logTerminalRef.current.scrollHeight;
    }
  }, [job.logs]);

  const isCompleted = job.status === 'completed';
  const isFailed = job.status === 'failed';
  const isRunning = !isCompleted && !isFailed && job.status !== 'cancelled';

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header status bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-800 gap-3">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="font-bold text-lg text-white">{job.name}</span>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
              isCompleted
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                : isFailed
                ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                : 'bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse'
            }`}>
              {job.current_stage || job.status}
            </span>
            {job.is_mock && (
              <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-400 border border-slate-700">
                Mock Mode
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">{job.message}</p>
        </div>

        <div className="flex items-center space-x-3">
          {isRunning && (
            <button
              onClick={() => onCancel(job.job_id)}
              className="px-3 py-1.5 rounded-lg border border-red-800/80 hover:bg-red-950/40 text-red-400 text-xs font-medium transition-colors"
            >
              Cancel Pipeline
            </button>
          )}
          {isCompleted && (
            <button
              onClick={onViewResults}
              className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition-all shadow-lg shadow-emerald-600/20"
            >
              Launch 3D Viewer & Tools
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div>
        <div className="flex justify-between items-center text-xs text-slate-400 mb-1.5 font-medium">
          <span>Overall Pipeline Progress</span>
          <span className="font-mono text-emerald-400 font-bold">{Math.round(job.progress)}%</span>
        </div>
        <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden p-0.5 border border-slate-800">
          <div
            className="h-full bg-gradient-to-r from-teal-500 to-emerald-500 rounded-full transition-all duration-500 ease-out shadow-sm shadow-emerald-500/50"
            style={{ width: `${Math.max(3, job.progress)}%` }}
          />
        </div>
      </div>

      {/* 10-Stage Pipeline Visualizer */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1">
        {STAGES.map((s, idx) => {
          const stageIndex = idx + 1;
          const currentStageIndex = Math.min(10, Math.floor(job.progress / 10) + 1);
          const isDone = isCompleted || (job.progress >= stageIndex * 10);
          const isCurrent = isRunning && currentStageIndex === stageIndex;

          const IconComponent = s.icon;

          return (
            <div
              key={s.id}
              className={`p-2.5 rounded-xl border text-xs flex items-center space-x-2 transition-all ${
                isDone
                  ? 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
                  : isCurrent
                  ? 'bg-amber-950/30 border-amber-500/50 text-amber-200 shadow-md shadow-amber-500/10'
                  : 'bg-slate-950/40 border-slate-800/80 text-slate-500'
              }`}
            >
              <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${
                isDone ? 'bg-emerald-500/20 text-emerald-400' : isCurrent ? 'bg-amber-500/20 text-amber-400 animate-spin' : 'bg-slate-800 text-slate-600'
              }`}>
                {isCurrent ? <RotateCw className="w-3 h-3" /> : isDone ? <CheckCircle2 className="w-3 h-3" /> : <IconComponent className="w-3 h-3" />}
              </div>
              <span className="truncate font-medium">{s.label}</span>
            </div>
          );
        })}
      </div>

      {/* Real-time Reconstruction Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs">
        <div>
          <span className="text-slate-500 block text-[10px] uppercase tracking-wider">Frames (Sharp/Total)</span>
          <span className="font-mono text-slate-200 font-semibold">{job.metrics?.sharp_frames || 0} / {job.metrics?.total_frames || 0}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase tracking-wider">Dynamic Masked</span>
          <span className="font-mono text-amber-400 font-semibold">{job.metrics?.dynamic_objects_detected ?? 0} moving obj</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase tracking-wider">Fused 3D Points</span>
          <span className="font-mono text-emerald-400 font-semibold">{(job.metrics?.dense_points_count || 0).toLocaleString()}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase tracking-wider">Mesh Faces</span>
          <span className="font-mono text-slate-200 font-semibold">{(job.metrics?.mesh_faces_count || 0).toLocaleString()}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase tracking-wider">Mean Confidence</span>
          <span className="font-mono text-blue-400 font-semibold">{((job.metrics?.mean_confidence || 0) * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase tracking-wider">Georeference</span>
          <span className="font-mono text-emerald-300 font-semibold truncate block" title={job.metrics?.utm_zone}>
            {job.metrics?.utm_zone ? 'UTM Zone 43N' : 'WGS84'}
          </span>
        </div>
      </div>

      {/* Live Pipeline Terminal Logs */}
      <div>
        <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
          <div className="flex items-center space-x-2">
            <Terminal className="w-3.5 h-3.5 text-emerald-400" />
            <span className="font-semibold text-slate-300">Pipeline Execution Stream</span>
          </div>
          <span className="text-[10px] text-slate-500">Live stdout / telemetry sync</span>
        </div>
        <div
          ref={logTerminalRef}
          className="bg-black/80 rounded-xl p-3.5 border border-slate-800 font-mono text-[11px] text-emerald-400/90 h-36 overflow-y-auto space-y-1 shadow-inner"
        >
          {job.logs && job.logs.length > 0 ? (
            job.logs.map((line, i) => (
              <div key={i} className="leading-relaxed whitespace-pre-wrap">
                <span className="text-slate-500 mr-2">&gt;</span>
                {line}
              </div>
            ))
          ) : (
            <div className="text-slate-600 italic">Waiting for pipeline worker signals...</div>
          )}
        </div>
      </div>
    </div>
  );
};
