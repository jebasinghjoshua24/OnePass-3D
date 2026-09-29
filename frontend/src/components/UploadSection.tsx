import React, { useState, useRef } from 'react';
import { Upload, Video, FileText, Sliders, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';

interface UploadSectionProps {
  onSubmit: (formData: FormData) => void;
  onTriggerMock: () => void;
  isProcessing: boolean;
}

export const UploadSection: React.FC<UploadSectionProps> = ({ onSubmit, onTriggerMock, isProcessing }) => {
  const [name, setName] = useState('Aerial Infrastructure Survey #1');
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [telemetryFile, setTelemetryFile] = useState<File | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [fps, setFps] = useState('3.0');
  const [sharpnessThreshold, setSharpnessThreshold] = useState('85.0');
  const [error, setError] = useState<string | null>(null);

  const videoInputRef = useRef<HTMLInputElement>(null);
  const telemetryInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // If no video is selected, suggest mock mode or launch mock directly
    if (!videoFile) {
      onTriggerMock();
      return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('is_mock', 'false');
    formData.append('video', videoFile);
    if (telemetryFile) {
      formData.append('telemetry', telemetryFile);
    }

    onSubmit(formData);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      <div className="absolute top-0 right-0 w-80 h-80 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-800 gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>Input Flight Data</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-normal">
              Single-Pass Monocular
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Accepts 1080p/4K single-pass drone video (MP4/MOV) and synchronized GPS telemetry (CSV/JSON).
          </p>
        </div>

        <button
          type="button"
          onClick={onTriggerMock}
          disabled={isProcessing}
          className="inline-flex items-center space-x-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-emerald-600/30 to-teal-600/30 border border-emerald-500/40 hover:border-emerald-500 text-emerald-300 text-xs font-medium transition-all shadow hover:shadow-emerald-500/10"
        >
          <Sparkles className="w-4 h-4 text-emerald-400" />
          <span>Load Synthetic Demo Scene</span>
        </button>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 space-y-6">
        {/* Survey Name */}
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">Survey Mission Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-200 focus:outline-none focus:border-emerald-500 transition-colors"
            placeholder="e.g. Commercial Building Drone Inspection"
          />
        </div>

        {/* Dropzones Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Drone Video Dropzone */}
          <div
            onClick={() => videoInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[160px] ${
              videoFile
                ? 'border-emerald-500/60 bg-emerald-950/20'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/50 hover:bg-slate-950'
            }`}
          >
            <input
              ref={videoInputRef}
              type="file"
              accept="video/mp4,video/quicktime,video/x-matroska"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setVideoFile(e.target.files[0]);
                }
              }}
            />
            {videoFile ? (
              <div className="flex flex-col items-center">
                <CheckCircle2 className="w-9 h-9 text-emerald-400 mb-2" />
                <span className="text-sm font-semibold text-white break-all max-w-[240px] truncate">{videoFile.name}</span>
                <span className="text-xs text-slate-400 mt-0.5">{(videoFile.size / (1024 * 1024)).toFixed(1)} MB</span>
                <span className="text-[11px] text-emerald-400 mt-2 hover:underline">Click to change video</span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center mb-2.5 text-slate-400">
                  <Video className="w-5 h-5 text-emerald-400" />
                </div>
                <span className="text-sm font-medium text-slate-200">Upload Drone Video</span>
                <span className="text-xs text-slate-500 mt-1">MP4, MOV up to 4K (Auto-downscaled to 720p on CPU)</span>
              </div>
            )}
          </div>

          {/* Telemetry Dropzone */}
          <div
            onClick={() => telemetryInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[160px] ${
              telemetryFile
                ? 'border-blue-500/60 bg-blue-950/20'
                : 'border-slate-800 hover:border-slate-700 bg-slate-950/50 hover:bg-slate-950'
            }`}
          >
            <input
              ref={telemetryInputRef}
              type="file"
              accept=".csv,.json,.txt"
              className="hidden"
              onChange={(e) => {
                if (e.target.files && e.target.files[0]) {
                  setTelemetryFile(e.target.files[0]);
                }
              }}
            />
            {telemetryFile ? (
              <div className="flex flex-col items-center">
                <CheckCircle2 className="w-9 h-9 text-blue-400 mb-2" />
                <span className="text-sm font-semibold text-white break-all max-w-[240px] truncate">{telemetryFile.name}</span>
                <span className="text-xs text-slate-400 mt-0.5">{(telemetryFile.size / 1024).toFixed(1)} KB</span>
                <span className="text-[11px] text-blue-400 mt-2 hover:underline">Click to replace telemetry</span>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <div className="w-10 h-10 rounded-full bg-slate-800 flex items-center justify-center mb-2.5 text-slate-400">
                  <FileText className="w-5 h-5 text-blue-400" />
                </div>
                <span className="text-sm font-medium text-slate-200">GPS & Flight Telemetry</span>
                <span className="text-xs text-slate-500 mt-1">CSV/JSON (timestamp, lat, lon, alt, roll, pitch, yaw)</span>
              </div>
            )}
          </div>
        </div>

        {/* Advanced Parameters Toggle */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>{showAdvanced ? 'Hide Pipeline Configuration' : 'Configure Reconstruction Parameters (FPS, Blur Threshold)'}</span>
          </button>

          {showAdvanced && (
            <div className="mt-3 p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Keyframe Extraction Rate (FPS)</label>
                <input
                  type="number"
                  step="0.5"
                  min="1.0"
                  max="10.0"
                  value={fps}
                  onChange={(e) => setFps(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
                <span className="text-[10px] text-slate-500">Recommended: 2.0 - 5.0 FPS for optimal overlap</span>
              </div>
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Sharpness Threshold (Laplacian Var)</label>
                <input
                  type="number"
                  step="5"
                  min="20"
                  max="250"
                  value={sharpnessThreshold}
                  onChange={(e) => setSharpnessThreshold(e.target.value)}
                  className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200"
                />
                <span className="text-[10px] text-slate-500">Filters frames with motion blur below score</span>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-900/30 border border-red-800/50 flex items-center space-x-2 text-xs text-red-300">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Submit Action */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="submit"
            disabled={isProcessing}
            className={`px-6 py-3 rounded-xl font-medium text-sm transition-all flex items-center space-x-2 ${
              isProcessing
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20 active:scale-[0.99]'
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>{videoFile ? 'Start 3D Reconstruction Pipeline' : 'Run Demonstration Survey (Mock Mode)'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
