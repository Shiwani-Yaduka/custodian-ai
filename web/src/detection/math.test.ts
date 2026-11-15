import { describe, expect, it } from 'vitest';
import { calculateBaseline, computeAudioLevel, extractFeaturesFromLandmarks } from './math';
import { NormalizedLandmark, RawFaceSample } from '../types';

describe('MediaPipe Facial Landmark Mathematics', () => {
  it('returns face_present: false when landmarks array is empty or partial', () => {
    const emptyResult = extractFeaturesFromLandmarks([]);
    expect(emptyResult.face_present).toBe(false);
    expect(emptyResult.face_count).toBe(0);
    expect(emptyResult.face_size).toBe(0.0);

    const partialLandmarks = new Array(100).fill({ x: 0.5, y: 0.5, z: 0.0 });
    const partialResult = extractFeaturesFromLandmarks(partialLandmarks);
    expect(partialResult.face_present).toBe(false);
  });

  it('computes centered face geometry when looking directly ahead', () => {
    // Construct 478 mock landmarks looking centered
    const mockLandmarks: NormalizedLandmark[] = new Array(478).fill(null).map(() => ({
      x: 0.5,
      y: 0.5,
      z: 0.0,
    }));

    // Specific landmark placements for centered face
    mockLandmarks[1] = { x: 0.5, y: 0.5, z: 0.0 }; // Nose tip
    mockLandmarks[10] = { x: 0.5, y: 0.2, z: 0.0 }; // Forehead
    mockLandmarks[152] = { x: 0.5, y: 0.8, z: 0.0 }; // Chin
    mockLandmarks[234] = { x: 0.3, y: 0.5, z: 0.0 }; // Left cheek
    mockLandmarks[454] = { x: 0.7, y: 0.5, z: 0.0 }; // Right cheek

    // Left eye (span from x=0.35 to 0.45, center is 0.40)
    mockLandmarks[33] = { x: 0.35, y: 0.4, z: 0.0 };
    mockLandmarks[133] = { x: 0.45, y: 0.4, z: 0.0 };
    mockLandmarks[468] = { x: 0.40, y: 0.4, z: 0.0 }; // Left iris centered

    // Right eye (span from x=0.55 to 0.65, center is 0.60)
    mockLandmarks[362] = { x: 0.55, y: 0.4, z: 0.0 };
    mockLandmarks[263] = { x: 0.65, y: 0.4, z: 0.0 };
    mockLandmarks[473] = { x: 0.60, y: 0.4, z: 0.0 }; // Right iris centered

    const result = extractFeaturesFromLandmarks(mockLandmarks);
    expect(result.face_present).toBe(true);
    expect(result.face_count).toBe(1);
    expect(result.head_yaw).toBeCloseTo(0.0, 1);
    expect(result.head_pitch).toBeCloseTo(0.0, 1);
    expect(result.head_roll).toBeCloseTo(0.0, 1);
    expect(result.gaze_offset_x).toBeCloseTo(0.0, 2);
    expect(result.face_size).toBeGreaterThan(0.2);
  });

  it('detects head turn to the right when nose shifts rightwards', () => {
    const mockLandmarks: NormalizedLandmark[] = new Array(478).fill(null).map(() => ({
      x: 0.5,
      y: 0.5,
      z: 0.0,
    }));

    mockLandmarks[10] = { x: 0.5, y: 0.2, z: 0.0 }; // Forehead
    mockLandmarks[152] = { x: 0.5, y: 0.8, z: 0.0 }; // Chin
    mockLandmarks[234] = { x: 0.3, y: 0.5, z: 0.0 }; // Left cheek
    mockLandmarks[454] = { x: 0.7, y: 0.5, z: 0.0 }; // Right cheek
    mockLandmarks[1] = { x: 0.62, y: 0.5, z: 0.0 }; // Nose shifted right

    mockLandmarks[33] = { x: 0.35, y: 0.4, z: 0.0 };
    mockLandmarks[133] = { x: 0.45, y: 0.4, z: 0.0 };
    mockLandmarks[468] = { x: 0.40, y: 0.4, z: 0.0 };
    mockLandmarks[362] = { x: 0.55, y: 0.4, z: 0.0 };
    mockLandmarks[263] = { x: 0.65, y: 0.4, z: 0.0 };
    mockLandmarks[473] = { x: 0.60, y: 0.4, z: 0.0 };

    const result = extractFeaturesFromLandmarks(mockLandmarks);
    expect(result.head_yaw).toBeGreaterThan(20.0); // > 20 degrees yaw
  });

  it('calculates mean and standard deviation for calibration baseline', () => {
    const samples: RawFaceSample[] = [
      {
        timestamp: 1000,
        face_present: true,
        face_count: 1,
        gaze_offset_x: 0.10,
        gaze_offset_y: 0.0,
        head_yaw: 2.0,
        head_pitch: -1.0,
        head_roll: 0.5,
        face_size: 0.35,
        ambient_light: 0.8,
      },
      {
        timestamp: 1200,
        face_present: true,
        face_count: 1,
        gaze_offset_x: 0.12,
        gaze_offset_y: 0.0,
        head_yaw: 4.0,
        head_pitch: 1.0,
        head_roll: 0.3,
        face_size: 0.36,
        ambient_light: 0.8,
      },
      {
        timestamp: 1400,
        face_present: true,
        face_count: 1,
        gaze_offset_x: 0.08,
        gaze_offset_y: 0.0,
        head_yaw: 0.0,
        head_pitch: 0.0,
        head_roll: 0.4,
        face_size: 0.34,
        ambient_light: 0.8,
      },
    ];

    const baseline = calculateBaseline(samples);
    expect(baseline.sample_count).toBe(3);
    expect(baseline.mean_head_yaw).toBeCloseTo(2.0, 1);
    expect(baseline.std_head_yaw).toBeGreaterThan(1.0);
    expect(baseline.mean_face_size).toBeCloseTo(0.35, 2);
    expect(baseline.mean_gaze_offset).toBeCloseTo(0.10, 2);
  });

  it('provides safe default calibration values when fewer than 2 valid samples exist', () => {
    const baseline = calculateBaseline([]);
    expect(baseline.sample_count).toBe(0);
    expect(baseline.mean_gaze_offset).toBe(0.15);
    expect(baseline.std_gaze_offset).toBe(0.05);
  });
});

describe('Web Audio RMS Volume Calculation', () => {
  it('returns 0.0 when buffer is empty or completely silent (all 128)', () => {
    const silent = new Uint8Array(128).fill(128); // 128 is center (0 amplitude)
    expect(computeAudioLevel(silent)).toBeCloseTo(0.0, 3);
  });

  it('measures non-zero volume for noisy waveform', () => {
    const noisy = new Uint8Array(128);
    for (let i = 0; i < 128; i++) {
      noisy[i] = i % 2 === 0 ? 180 : 76; // Oscillating sound wave
    }
    const level = computeAudioLevel(noisy);
    expect(level).toBeGreaterThan(0.3);
    expect(level).toBeLessThanOrEqual(1.0);
  });
});
