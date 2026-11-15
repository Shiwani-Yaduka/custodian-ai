/**
 * MediaPipe Face Landmarker wrapper.
 * Runs 100% offline using local WASM in /wasm and model in /models/face_landmarker.task.
 * Extracts landmark geometry and discards video pixels immediately.
 */
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision';
import { RawFaceSample } from '../types';
import { extractFeaturesFromLandmarks } from './math';

export class FaceDetector {
  private landmarker: FaceLandmarker | null = null;
  private isInitializing: boolean = false;
  private isReady: boolean = false;
  private lastProcessedTime: number = 0;

  public async initialize(): Promise<void> {
    if (this.isReady || this.isInitializing) return;
    this.isInitializing = true;

    try {
      // Load wasm files from local public/wasm directory
      const vision = await FilesetResolver.forVisionTasks('/wasm');

      // Create FaceLandmarker using local task model
      this.landmarker = await FaceLandmarker.createFromOptions(vision, {
        baseOptions: {
          modelAssetPath: '/models/face_landmarker.task',
          delegate: 'CPU', // CPU delegate is light, stable, and laptop-friendly
        },
        runningMode: 'VIDEO',
        numFaces: 2, // Enable detecting multiple faces if a second person appears
        minFaceDetectionConfidence: 0.5,
        minFacePresenceConfidence: 0.5,
        minTrackingConfidence: 0.5,
        outputFaceBlendshapes: false,
        outputFacialTransformationMatrixes: false,
      });

      this.isReady = true;
      console.log('[FaceDetector] MediaPipe Face Landmarker initialized successfully (CPU, offline mode).');
    } catch (err) {
      console.error('[FaceDetector] Failed to initialize MediaPipe Face Landmarker:', err);
      throw err;
    } finally {
      this.isInitializing = false;
    }
  }

  /**
   * Process a single video frame and extract abstract features.
   */
  public processVideoFrame(video: HTMLVideoElement, timestampMs: number = performance.now()): RawFaceSample {
    const emptySample: RawFaceSample = {
      timestamp: Date.now(),
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

    if (!this.isReady || !this.landmarker || video.readyState < 2) {
      return emptySample;
    }

    // MediaPipe requires strictly monotonically increasing timestamps
    const now = Math.max(timestampMs, this.lastProcessedTime + 1);
    this.lastProcessedTime = now;

    try {
      const result = this.landmarker.detectForVideo(video, now);
      const faceCount = result.faceLandmarks.length;

      if (faceCount === 0) {
        return emptySample;
      }

      // Process primary face
      const primaryLandmarks = result.faceLandmarks[0];
      const sample = extractFeaturesFromLandmarks(primaryLandmarks, Date.now());
      sample.face_count = faceCount;
      return sample;
    } catch (err) {
      console.warn('[FaceDetector] Detection frame error:', err);
      return emptySample;
    }
  }

  public close() {
    if (this.landmarker) {
      this.landmarker.close();
      this.landmarker = null;
    }
    this.isReady = false;
  }
}
