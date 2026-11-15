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
