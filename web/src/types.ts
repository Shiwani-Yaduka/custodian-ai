/**
 * TypeScript type definitions for Custodian AI student web application.
 */

export interface FeatureBatch {
  session_id: string;
  timestamp: number;
  face_present: boolean;
  face_count: number;
  gaze_offset_x: number;
  gaze_offset_y: number;
  head_pitch: number;
  head_yaw: number;
  head_roll: number;
  window_focused: boolean;
  tab_visible: boolean;
  audio_level: number;
  network_heartbeat_ok: boolean;
  camera_track_active: boolean;
  fps: number;
  ambient_light: number;
}

export interface CalibrationBaseline {
  mean_gaze_offset: number;
  std_gaze_offset: number;
  mean_head_yaw: number;
  std_head_yaw: number;
  mean_head_pitch: number;
  std_head_pitch: number;
  mean_face_size: number;
  std_face_size: number;
  sample_count: number;
}

export interface RawFaceSample {
  timestamp: number;
  face_present: boolean;
  face_count: number;
  gaze_offset_x: number;
  gaze_offset_y: number;
  head_yaw: number;
  head_pitch: number;
  head_roll: number;
  face_size: number;
  ambient_light: number;
}

export interface NormalizedLandmark {
  x: number;
  y: number;
  z: number;
}

export interface UserSession {
  token: string;
  user_id: number;
  username: string;
  role: string;
}

export interface Question {
  id: string;
  type: 'mcq' | 'written';
  prompt: string;
  options?: string[];
}

export interface Exam {
  id: number;
  title: string;
  description: string;
  duration_minutes: number;
  questions: Question[];
}

export interface ExamSession {
  id: string;
  exam_id: number;
  user_id: number;
  start_time: string;
  status: string;
}

export interface WarningNotification {
  level: string; // 'WARNED' | 'ELEVATED'
  reason: string;
  timestamp: number;
  time_added_minutes?: number;
}

export interface ProbeRequest {
  probe_name: string;
  type: string;
  message?: string;
  session_id: string;
}

export interface StudentTimelineItem {
  timestamp: string;
  elapsed_seconds: number;
  type: string;
  title: string;
  description: string;
  severity: 'info' | 'warning' | 'alert';
}

export interface HeldSessionItem {
  session_id: string;
  paused_at: number;
  evidence_summary: string;
  status: string;
}

export interface FacultyProbeDetail {
  probe_name: string;
  outcome: string;
  cost: number;
  posterior: string;
}

export interface FacultyCaseDetail {
  case_id: string;
  open_reason: string;
  is_open: boolean;
  resolution?: string;
  multiplier: number;
  opened_at: number;
  resolved_at?: number;
  probes: FacultyProbeDetail[];
}

export interface FacultyRiskPoint {
  timestamp: number;
  score: number;
  from_tier: string;
  to_tier: string;
  candidate_tier: string;
  gate_passed: boolean;
  reason: string;
  blocked_reason?: string;
  stub_clip_marker?: string;
}

export interface FacultyTimeline {
  session_id: string;
  status: string;
  start_time: number;
  peak_risk_score: number;
  risk_points: FacultyRiskPoint[];
  investigation_cases: FacultyCaseDetail[];
  warnings_issued: Array<{ level: number; reason: string; timestamp: number }>;
  student_explanations: Array<{ explanation_text: string; submitted_at: number }>;
  hold_summary?: string;
  faculty_decisions: Array<{ faculty_id: number; verdict: string; notes?: string; recorded_at: number }>;
  observations: Array<{
    timestamp: number;
    signal: string;
    duration: number;
    confidence: number;
    plain_summary: string;
  }>;
  recommendation: string;
}

export interface ScenarioStep {
  timestamp: number;
  elapsed_seconds: number;
  description: string;
  risk_score: number;
  current_tier: string;
  candidate_tier: string;
  channel_bars: Record<string, number>;
  active_channels_count: number;
  open_case_posterior?: Record<string, number>;
  gate_checklist: Record<string, boolean>;
  warning_issued?: string;
  is_held: boolean;
}

export interface ScenarioResult {
  scenario_id: string;
  title: string;
  description: string;
  expected_outcome: string;
  actual_outcome: string;
  passed: boolean;
  final_score: number;
  final_tier: string;
  resolution?: string;
  warnings_count: number;
  is_held: boolean;
  system_notice?: string;
  steps: ScenarioStep[];
}

export interface ScenarioMeta {
  id: string;
  title: string;
  expected: string;
  description: string;
}

export interface MassFlagStatus {
  triggered: boolean;
  notice?: string;
  relaxation_factor: number;
  affected_ratio: number;
  updated_at: number;
}
