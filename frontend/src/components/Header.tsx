import React from 'react';
import { Layers, Cpu, ShieldCheck, PlayCircle, Activity } from 'lucide-react';
import { SystemHealth } from '../services/api';

interface HeaderProps {
  health: SystemHealth | null;
  onTriggerMock: () => void;
  isProcessing: boolean;
}

export const Header: React.FC<HeaderProps> = ({ health, onTriggerMock, isProcessing }) => {
  const isCuda = health?.hardware.cuda_available ?? false;

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-50 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand / Logo */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Layers className="w-5 h-5 text-slate-950 font-bold" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight text-white">OnePass-3D</span>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                SIH Problem #26158
              </span>
            </div>
            <p className="text-xs text-slate-400">
              One-Pass Drone Video to Georeferenced 3D Model System (NTRO)
            </p>
          </div>
        </div>

        {/* Hardware Status & Quick Actions */}
        <div className="flex items-center space-x-4">
          <div className="hidden sm:flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-xs">
            <Cpu className="w-4 h-4 text-emerald-400" />
            <span className="text-slate-300">
              Engine: <strong className="text-emerald-400 font-mono">{isCuda ? 'CUDA GPU' : 'CPU (720p)'}</strong>
            </span>
            <span className="text-slate-500">•</span>
            <ShieldCheck className="w-4 h-4 text-blue-400" />
            <span className="text-slate-300">Confidence-Aware</span>
          </div>

          <button
            onClick={onTriggerMock}
            disabled={isProcessing}
            className={`flex items-center space-x-2 px-4 py-2 rounded-lg font-medium text-xs transition-all shadow-md ${
              isProcessing
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 hover:scale-[1.02] active:scale-[0.98]'
            }`}
          >
            {isProcessing ? (
              <>
                <Activity className="w-4 h-4 animate-spin text-emerald-400" />
                <span>Pipeline Running...</span>
              </>
            ) : (
              <>
                <PlayCircle className="w-4 h-4" />
                <span>Instant Demo (Mock Mode)</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
