import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { UploadSection } from './components/UploadSection';
import { JobStatusTracker } from './components/JobStatusTracker';
import { Viewer3D } from './components/Viewer3D';
import { MeasurementTools } from './components/MeasurementTools';
import { ConfidenceInspector } from './components/ConfidenceInspector';
import { TelemetryPanel } from './components/TelemetryPanel';
import { ExportModal } from './components/ExportModal';
import { 
  fetchHealth, createJob, createMockJob, getJob, cancelJob, 
  JobRecord, SystemHealth 
} from './services/api';
import { Download, Layers, ShieldCheck, Activity, RefreshCw } from 'lucide-react';

export function App() {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [activeJob, setActiveJob] = useState<JobRecord | null>(null);
  const [activeTab, setActiveTab] = useState<'viewer' | 'telemetry' | 'confidence'>('viewer');
  const [showExportModal, setShowExportModal] = useState(false);

  // Measurement State
  const [measurementMode, setMeasurementMode] = useState<'none' | 'distance' | 'height' | 'area'>('none');
  const [measurementHistory, setMeasurementHistory] = useState<Array<{
    type: string;
    value: number;
    details: string;
    timestamp: string;
  }>>([
    { type: 'distance', value: 20.0, details: 'Building facade length: 20.00 m', timestamp: '10:04' },
    { type: 'height', value: 11.2, details: 'Rooftop vertical elevation clearance: 11.20 m', timestamp: '10:05' },
    { type: 'area', value: 280.0, details: 'Estimated building footprint area: 280.0 m²', timestamp: '10:07' },
  ]);
  const [confidenceFilter, setConfidenceFilter] = useState(0.40);
  const [startingDemo, setStartingDemo] = useState(false);

  // 1. Initial health fetch
  useEffect(() => {
    fetchHealth()
      .then(setHealth)
      .catch((err) => console.warn('Could not contact API health check:', err));
  }, []);

  // 2. Poll active job status if running
  useEffect(() => {
    if (!activeJob) return;

    const isRunning = !['completed', 'failed', 'cancelled'].includes(activeJob.status);
    if (!isRunning) return;

    const interval = setInterval(() => {
      getJob(activeJob.job_id)
        .then(setActiveJob)
        .catch((err) => console.warn('Job poll error:', err));
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob?.job_id, activeJob?.status]);

  const handleTriggerMock = async () => {
    if (startingDemo) return;
    setStartingDemo(true);
    try {
      const mockJob = await createMockJob('OnePass-3D Synthetic Demo Survey');
      setActiveJob(mockJob);
    } catch (err: any) {
      alert(`Could not start mock job: ${err.message}`);
    } finally {
      setStartingDemo(false);
    }
  };

  const handleUploadSubmit = async (formData: FormData) => {
    try {
      const newJob = await createJob(formData);
      setActiveJob(newJob);
    } catch (err: any) {
      alert(`Could not start job: ${err.message}`);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await cancelJob(jobId);
      if (activeJob) {
        setActiveJob({ ...activeJob, status: 'cancelled', message: 'Cancelled by user' });
      }
    } catch (err: any) {
      console.error('Cancel error:', err);
    }
  };

  const handleMeasurementComplete = (type: string, value: number, details: string) => {
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMeasurementHistory((prev) => [
      { type, value, details, timestamp: timeStr },
      ...prev,
    ]);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header
        health={health}
        onTriggerMock={handleTriggerMock}
        isProcessing={startingDemo || (activeJob ? !['completed', 'failed', 'cancelled'].includes(activeJob.status) : false)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Upload & Mission Setup Section */}
        <UploadSection
          onSubmit={handleUploadSubmit}
          onTriggerMock={handleTriggerMock}
          isProcessing={startingDemo || (activeJob ? !['completed', 'failed', 'cancelled'].includes(activeJob.status) : false)}
        />

        {/* Pipeline Execution Tracker (Visible when a job is active or completed) */}
        {activeJob && (
          <JobStatusTracker
            job={activeJob}
            onCancel={handleCancelJob}
            onViewResults={() => setActiveTab('viewer')}
          />
        )}

        {/* 3D Model Reconstruction & Analysis Section */}
        {activeJob && activeJob.progress > 50 && (
          <div className="space-y-4">
            {/* View Navigation Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-2 border-b border-slate-800 gap-3">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setActiveTab('viewer')}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-all ${
                    activeTab === 'viewer'
                      ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/20'
                      : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                  }`}
                >
                  <Layers className="w-4 h-4" />
                  <span>Interactive 3D Model & Potree/Three.js</span>
                </button>

                <button
                  onClick={() => setActiveTab('confidence')}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-all ${
                    activeTab === 'confidence'
                      ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                      : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                  }`}
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>Confidence Heatmap Analysis</span>
                </button>

                <button
                  onClick={() => setActiveTab('telemetry')}
                  className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-2 transition-all ${
                    activeTab === 'telemetry'
                      ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/20'
                      : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                  }`}
                >
                  <Activity className="w-4 h-4" />
                  <span>Flight Trajectory & GPS</span>
                </button>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowExportModal(true)}
                  className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold transition-all shadow-md shadow-emerald-600/20 flex items-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>Export .PLY / .GLB / GeoTIFF</span>
                </button>
              </div>
            </div>

            {/* Main 3D Viewer & Tools Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
              {/* Left 2 Cols: 3D Three.js Canvas */}
              <div className="lg:col-span-2 space-y-4">
                <Viewer3D
                  job={activeJob}
                  measurementMode={measurementMode}
                  onMeasurementComplete={handleMeasurementComplete}
                  confidenceFilter={confidenceFilter}
                />

                {/* Bottom Details Tabs */}
                {activeTab === 'telemetry' && <TelemetryPanel job={activeJob} />}
                {activeTab === 'confidence' && (
                  <ConfidenceInspector
                    job={activeJob}
                    confidenceFilter={confidenceFilter}
                    onConfidenceFilterChange={setConfidenceFilter}
                  />
                )}
              </div>

              {/* Right Col: Measurement Tools & Metrics Panel */}
              <div className="space-y-4">
                <MeasurementTools
                  job={activeJob}
                  currentMode={measurementMode}
                  onSetMode={setMeasurementMode}
                  measurementHistory={measurementHistory}
                  onClearHistory={() => setMeasurementHistory([])}
                />

                {activeTab === 'viewer' && (
                  <ConfidenceInspector
                    job={activeJob}
                    confidenceFilter={confidenceFilter}
                    onConfidenceFilterChange={setConfidenceFilter}
                  />
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Export Outputs Modal */}
      {showExportModal && activeJob && (
        <ExportModal job={activeJob} onClose={() => setShowExportModal(false)} />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 px-6 text-center text-xs text-slate-500">
        SinglePass3D Prototype • Problem Statement #26158 • National Technical Research Organisation (NTRO) • SIH
      </footer>
    </div>
  );
}

export default App;
