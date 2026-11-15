/**
 * Pure geometric and statistical functions for facial feature extraction.
 * Tested with Vitest without DOM or browser dependencies.
 */
import { CalibrationBaseline, NormalizedLandmark, RawFaceSample } from '../types';

// Key MediaPipe 478 Landmark Indices
export const LANDMARK_INDICES = {
  NOSE_TIP: 1,
  FOREHEAD: 10,
  CHIN: 152,
  LEFT_CHEEK: 234,
  RIGHT_CHEEK: 454,
  LEFT_EYE_OUTER: 33,
  LEFT_EYE_INNER: 133,
  RIGHT_EYE_INNER: 362,
  RIGHT_EYE_OUTER: 263,
  LEFT_IRIS_CENTER: 468,
  RIGHT_IRIS_CENTER: 473,
};

/**
 * Extract abstract numerical features from 478 MediaPipe landmarks.
 * Never retains or transmits image pixels.
 */
export function extractFeaturesFromLandmarks(
  landmarks: NormalizedLandmark[],
  timestamp: number = Date.now()
): RawFaceSample {
  if (!landmarks || landmarks.length < 478) {
    return {
      timestamp,
      face_present: false,
      face_count: 0,
      gaze_offset_x: 0.0,
      gaze_offset_y: 0.0,
      head_yaw: 0.0,
      head_pitch: 0.0,
      head_roll: 0.0,
      face_size: 0.0,
      ambient_light: 0.8,
    };
  }

  const nose = landmarks[LANDMARK_INDICES.NOSE_TIP];
  const forehead = landmarks[LANDMARK_INDICES.FOREHEAD];
  const chin = landmarks[LANDMARK_INDICES.CHIN];
  const leftCheek = landmarks[LANDMARK_INDICES.LEFT_CHEEK];
  const rightCheek = landmarks[LANDMARK_INDICES.RIGHT_CHEEK];

  // 1. Face Size (bounding scale relative to frame)
  const faceWidth = Math.abs(rightCheek.x - leftCheek.x);
  const faceHeight = Math.abs(chin.y - forehead.y);
  const faceSize = Math.max(0.0, Math.min(1.0, Math.sqrt(faceWidth * faceHeight)));

  // 2. Head Yaw (horizontal rotation in degrees: approx -45 to +45)
  const faceCenterX = (leftCheek.x + rightCheek.x) / 2.0;
  const halfWidth = Math.max(0.01, faceWidth / 2.0);
  const normalizedYaw = Math.max(-1.5, Math.min(1.5, (nose.x - faceCenterX) / halfWidth));
  const headYaw = normalizedYaw * 45.0;

  // 3. Head Pitch (vertical tilt in degrees: approx -35 to +35)
  const faceCenterY = (forehead.y + chin.y) / 2.0;
  const halfHeight = Math.max(0.01, faceHeight / 2.0);
  const normalizedPitch = Math.max(-1.5, Math.min(1.5, (nose.y - faceCenterY) / halfHeight));
  const headPitch = normalizedPitch * 35.0;

  // 4. Head Roll (tilt angle between left and right eye in degrees)
  const leftEyeInner = landmarks[LANDMARK_INDICES.LEFT_EYE_INNER];
  const rightEyeInner = landmarks[LANDMARK_INDICES.RIGHT_EYE_INNER];
  const dy = rightEyeInner.y - leftEyeInner.y;
  const dx = rightEyeInner.x - leftEyeInner.x;
  const headRoll = (Math.atan2(dy, dx) * 180.0) / Math.PI;

  // 5. Gaze Offset (deviation from eye center)
  const leftIris = landmarks[LANDMARK_INDICES.LEFT_IRIS_CENTER];
  const leftEyeOuter = landmarks[LANDMARK_INDICES.LEFT_EYE_OUTER];
  const rightIris = landmarks[LANDMARK_INDICES.RIGHT_IRIS_CENTER];
  const rightEyeOuter = landmarks[LANDMARK_INDICES.RIGHT_EYE_OUTER];

  // Left Eye Iris Offset
  const leftSpanX = Math.abs(leftEyeInner.x - leftEyeOuter.x);
  let leftGazeX = 0.0;
  if (leftSpanX > 0.005) {
    const leftRatioX = (leftIris.x - Math.min(leftEyeOuter.x, leftEyeInner.x)) / leftSpanX;
    leftGazeX = (leftRatioX - 0.5) * 2.0;
  }

  // Right Eye Iris Offset
  const rightSpanX = Math.abs(rightEyeOuter.x - rightEyeInner.x);
  let rightGazeX = 0.0;
  if (rightSpanX > 0.005) {
    const rightRatioX = (rightIris.x - Math.min(rightEyeOuter.x, rightEyeInner.x)) / rightSpanX;
    rightGazeX = (rightRatioX - 0.5) * 2.0;
  }

  const gazeOffsetX = (leftGazeX + rightGazeX) / 2.0;
  const gazeOffsetY = 0.0; // MediaPipe vertical iris is subtle; horizontal yaw/gaze dominates

  return {
    timestamp,
    face_present: true,
    face_count: 1,
    gaze_offset_x: Number(gazeOffsetX.toFixed(4)),
    gaze_offset_y: Number(gazeOffsetY.toFixed(4)),
    head_yaw: Number(headYaw.toFixed(2)),
    head_pitch: Number(headPitch.toFixed(2)),
    head_roll: Number(headRoll.toFixed(2)),
    face_size: Number(faceSize.toFixed(4)),
    ambient_light: 0.8,
  };
}

/**
 * Compute the baseline mean and standard deviation from 30 seconds of calibration samples.
 */
export function calculateBaseline(samples: RawFaceSample[]): CalibrationBaseline {
  const validSamples = samples.filter((s) => s.face_present);
  const n = validSamples.length;

  if (n < 2) {
    return {
      mean_gaze_offset: 0.15,
      std_gaze_offset: 0.05,
      mean_head_yaw: 0.0,
      std_head_yaw: 0.08,
      mean_head_pitch: 0.0,
      std_head_pitch: 0.08,
      mean_face_size: 0.35,
      std_face_size: 0.05,
      sample_count: n,
    };
  }

  const calcStats = (getter: (s: RawFaceSample) => number) => {
    const values = validSamples.map(getter);
    const mean = values.reduce((sum, v) => sum + v, 0) / n;
    const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / (n - 1);
    const std = Math.max(0.01, Math.sqrt(variance));
    return { mean: Number(mean.toFixed(4)), std: Number(std.toFixed(4)) };
  };

  const gazeStats = calcStats((s) => Math.sqrt(s.gaze_offset_x * s.gaze_offset_x + s.gaze_offset_y * s.gaze_offset_y));
  const yawStats = calcStats((s) => s.head_yaw);
  const pitchStats = calcStats((s) => s.head_pitch);
  const sizeStats = calcStats((s) => s.face_size);

  return {
    mean_gaze_offset: gazeStats.mean,
    std_gaze_offset: gazeStats.std,
    mean_head_yaw: yawStats.mean,
    std_head_yaw: yawStats.std,
    mean_head_pitch: pitchStats.mean,
    std_head_pitch: pitchStats.std,
    mean_face_size: sizeStats.mean,
    std_face_size: sizeStats.std,
    sample_count: n,
  };
}

/**
 * Measure audio RMS energy from an array of byte frequency/time-domain data.
 * Produces a normalized volume level between 0.0 and 1.0 (level only, never speech).
 */
export function computeAudioLevel(data: Uint8Array): number {
  if (!data || data.length === 0) return 0.0;
  let sumSquares = 0.0;
  for (let i = 0; i < data.length; i++) {
    // Convert 0..255 byte to -1.0..1.0
    const normalized = (data[i] - 128) / 128.0;
    sumSquares += normalized * normalized;
  }
  const rms = Math.sqrt(sumSquares / data.length);
  return Number(Math.min(1.0, rms * 2.5).toFixed(4));
}
