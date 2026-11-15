/**
 * Sensory batcher and event monitor.
 * Collects features at 5 fps, monitors window/audio/network status,
 * and transmits 1-second batches to capture-detect (:8001).
 */
import { CONFIG } from '../config';
import { FeatureBatch, RawFaceSample } from '../types';

export interface BatcherCallbacks {
  onBatchSent?: (batch: FeatureBatch) => void;
  onAudioLevel?: (level: number) => void;
  onFpsUpdated?: (fps: number) => void;
  onError?: (err: Error) => void;
}

export class SensorBatcher {
  private sessionId: string;
  private isPractice: boolean;
  private callbacks: BatcherCallbacks;

  // Real-time environmental state
  private windowFocused: boolean = true;
  private tabVisible: boolean = true;
  private networkAlive: boolean = navigator.onLine;
  private cameraActive: boolean = true;
  private currentAudioLevel: number = 0.0;

  // Frame rate estimation
  private frameCount: number = 0;
  private lastFpsCalculation: number = Date.now();
  private currentFps: number = 0.0;

  // Sampling buffer
  private currentSample: RawFaceSample = {
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

  private batchTimer: ReturnType<typeof setInterval> | null = null;
  private audioContext: AudioContext | null = null;
  private audioAnalyser: AnalyserNode | null = null;
  private audioSource: MediaStreamAudioSourceNode | null = null;
  private audioBuffer: Uint8Array | null = null;
  private audioCheckTimer: ReturnType<typeof setInterval> | null = null;

  constructor(sessionId: string, isPractice: boolean = false, callbacks: BatcherCallbacks = {}) {
    this.sessionId = sessionId;
    this.isPractice = isPractice;
    this.callbacks = callbacks;

    this.setupWindowListeners();
  }

  private setupWindowListeners() {
    window.addEventListener('focus', this.handleFocus);
    window.addEventListener('blur', this.handleBlur);
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
  }

  private cleanupWindowListeners() {
    window.removeEventListener('focus', this.handleFocus);
    window.removeEventListener('blur', this.handleBlur);
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
  }

  private handleFocus = () => {
    this.windowFocused = true;
  };

  private handleBlur = () => {
    this.windowFocused = false;
  };

  private handleVisibilityChange = () => {
    this.tabVisible = !document.hidden;
  };

  private handleOnline = () => {
    this.networkAlive = true;
  };

  private handleOffline = () => {
    this.networkAlive = false;
  };

  /**
   * Initialize Web Audio API to monitor ambient sound level (volume only, never speech).
   */
  public attachAudioStream(stream: MediaStream) {
    try {
      const audioTracks = stream.getAudioTracks();
      if (audioTracks.length === 0) return;

      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.audioContext = new AudioCtx();
      this.audioAnalyser = this.audioContext.createAnalyser();
      this.audioAnalyser.fftSize = 256;
      this.audioBuffer = new Uint8Array(this.audioAnalyser.frequencyBinCount);

      this.audioSource = this.audioContext.createMediaStreamSource(stream);
      this.audioSource.connect(this.audioAnalyser);

      // Periodically measure volume RMS
      this.audioCheckTimer = setInterval(() => {
        if (!this.audioAnalyser || !this.audioBuffer) return;
        this.audioAnalyser.getByteTimeDomainData(this.audioBuffer as any);

        let sumSquares = 0.0;
        for (let i = 0; i < this.audioBuffer.length; i++) {
          const norm = (this.audioBuffer[i] - 128) / 128.0;
          sumSquares += norm * norm;
        }
        const rms = Math.sqrt(sumSquares / this.audioBuffer.length);
        this.currentAudioLevel = Number(Math.min(1.0, rms * 2.5).toFixed(4));
        this.callbacks.onAudioLevel?.(this.currentAudioLevel);
      }, 200);
    } catch (err) {
      console.warn('[SensorBatcher] Web Audio API init warning:', err);
    }
  }

  /**
   * Feed a new raw face landmark sample from the 5 fps detector loop.
   */
  public updateFaceSample(sample: RawFaceSample, cameraLive: boolean = true) {
    this.currentSample = sample;
    this.cameraActive = cameraLive;
    this.frameCount++;

    // Calculate rolling frame rate
    const now = Date.now();
    const elapsed = (now - this.lastFpsCalculation) / 1000.0;
    if (elapsed >= 1.0) {
      this.currentFps = Number((this.frameCount / elapsed).toFixed(1));
      this.frameCount = 0;
      this.lastFpsCalculation = now;
      this.callbacks.onFpsUpdated?.(this.currentFps);
    }
  }

  /**
   * Start 1-second interval batch dispatcher.
   */
  public start() {
    if (this.batchTimer) return;

    this.batchTimer = setInterval(() => {
      this.dispatchBatch();
    }, CONFIG.BATCH_INTERVAL_MS);
  }

  /**
   * Stop batcher and cleanup audio / window listeners.
   */
  public stop() {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }
    if (this.audioCheckTimer) {
      clearInterval(this.audioCheckTimer);
      this.audioCheckTimer = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch(() => {});
    }
    this.cleanupWindowListeners();
  }

  private async dispatchBatch() {
    const batch: FeatureBatch = {
      session_id: this.sessionId,
      timestamp: Date.now() / 1000.0,
      face_present: this.currentSample.face_present,
      face_count: this.currentSample.face_count,
      gaze_offset_x: this.currentSample.gaze_offset_x,
      gaze_offset_y: this.currentSample.gaze_offset_y,
      head_pitch: this.currentSample.head_pitch,
      head_yaw: this.currentSample.head_yaw,
      head_roll: this.currentSample.head_roll,
      window_focused: this.windowFocused,
      tab_visible: this.tabVisible,
      audio_level: this.currentAudioLevel,
      network_heartbeat_ok: this.networkAlive,
      camera_track_active: this.cameraActive,
      fps: this.currentFps > 0 ? this.currentFps : 5.0,
      ambient_light: this.currentSample.ambient_light,
    };

    this.callbacks.onBatchSent?.(batch);

    // If practice mode, do not send to real backend
    if (this.isPractice) return;

    try {
      const resp = await fetch(`${CONFIG.CAPTURE_DETECT_URL}/features`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batch),
      });

      if (!resp.ok) {
        console.warn(`[SensorBatcher] capture-detect returned status ${resp.status}`);
      }
    } catch (err) {
      this.callbacks.onError?.(err as Error);
    }
  }
}
