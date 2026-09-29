const API_BASE = (import.meta.env.VITE_API_URL || '') + '/api';

export interface ReconstructionMetrics {
  total_frames: number;
  sharp_frames: number;
  dynamic_objects_detected: number;
  sparse_points_count: number;
  dense_points_count: number;
  mesh_faces_count: number;
  mean_confidence: number;
  utm_zone: string;
}

export interface JobRecord {
  job_id: string;
  name: string;
  status: 'queued' | 'extracting' | 'sharpness_filtering' | 'preprocessing' | 'masking' | 
          'pose_estimation' | 'depth_estimation' | 'depth_fusion' | 'meshing' | 
          'georeferencing' | 'exporting' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_stage: string;
  message: string;
  error_message?: string;
  is_mock: boolean;
  video_filename?: string;
  telemetry_filename?: string;
  metrics: ReconstructionMetrics;
  artifacts: Record<string, string>;
  logs: string[];
  created_at?: string;
  updated_at?: string;
}

export interface SystemHealth {
  status: string;
  hardware: {
    device: 'cpu' | 'cuda';
    cuda_available: boolean;
    device_name: string;
    downscale_active: boolean;
  };
  config: {
    target_resolution: string;
    storage_dir: string;
    mock_mode: boolean;
  };
}

export async function fetchHealth(): Promise<SystemHealth> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('API server unreachable');
  return res.json();
}

export async function createJob(formData: FormData): Promise<JobRecord> {
  const res = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create job');
  }
  return res.json();
}

export async function createMockJob(name?: string): Promise<JobRecord> {
  const formData = new FormData();
  if (name) formData.append('name', name);
  const res = await fetch(`${API_BASE}/jobs/mock`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create mock demo job');
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<JobRecord> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error('Job not found');
  return res.json();
}

export async function listJobs(): Promise<JobRecord[]> {
  const res = await fetch(`${API_BASE}/jobs`);
  if (!res.ok) throw new Error('Failed to list jobs');
  return res.json();
}

export async function cancelJob(jobId: string): Promise<void> {
  await fetch(`${API_BASE}/jobs/${jobId}/cancel`, { method: 'POST' });
}

export function getArtifactDownloadUrl(jobId: string, filename: string): string {
  return `${API_BASE}/jobs/${jobId}/download/${filename}`;
}

export async function calibrateScale(
  jobId: string,
  pointA: [number, number, number],
  pointB: [number, number, number],
  realDistanceMeters: number
) {
  const res = await fetch(`${API_BASE}/jobs/calibrate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      job_id: jobId,
      point_a: pointA,
      point_b: pointB,
      real_distance_meters: realDistanceMeters,
    }),
  });
  return res.json();
}
