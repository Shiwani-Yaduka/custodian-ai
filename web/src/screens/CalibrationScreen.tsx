import React, { useEffect, useRef, useState } from 'react';
import { FaceDetector } from '../detection/faceLandmarker';
import { calculateBaseline } from '../detection/math';
import { CalibrationBaseline, RawFaceSample } from '../types';

interface CalibrationScreenProps {
  stream: MediaStream;
  detector: FaceDetector;
  onCalibrationComplete: (baseline: CalibrationBaseline) => void;
  isPractice: boolean;
}

export const CalibrationScreen: React.FC<CalibrationScreenProps> = ({
  stream,
  detector,
  onCalibrationComplete,
  isPractice,
}) => {
  const [secondsRemaining, setSecondsRemaining] = useState(30);
  const [samplesCount, setSamplesCount] = useState(0);
  const [currentSample, setCurrentSample] = useState<RawFaceSample | null>(null);
  const [feedback, setFeedback] = useState('Position your face comfortably inside the guide');

  const videoRef = useRef<HTMLVideoElement>(null);
  const samplesRef = useRef<RawFaceSample[]>([]);
  const isDoneRef = useRef(false);

  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(() => {});
    }

    const startTime = Date.now();
    const durationMs = 30 * 1000;

    // 5 FPS sampling loop (every 200ms)
    const sampleInterval = setInterval(() => {
      if (isDoneRef.current || !videoRef.current) return;

      const sample = detector.processVideoFrame(videoRef.current, performance.now());
      setCurrentSample(sample);

      if (sample.face_present) {
        samplesRef.current.push(sample);
        setSamplesCount(samplesRef.current.length);

        if (sample.face_count > 1) {
          setFeedback('⚠️ Multiple faces detected. Please ensure you are alone.');
        } else if (Math.abs(sample.head_yaw) > 20) {
          setFeedback('Please look forward towards the screen.');
        } else {
          setFeedback('✓ Great posture! Keep looking naturally at the screen.');
        }
      } else {
        setFeedback('⚠️ No face detected. Please face the camera.');
      }

      // Check countdown
      const elapsedMs = Date.now() - startTime;
      const remainingSec = Math.max(0, Math.ceil((durationMs - elapsedMs) / 1000));
      setSecondsRemaining(remainingSec);

      if (elapsedMs >= durationMs && !isDoneRef.current) {
        isDoneRef.current = true;
        clearInterval(sampleInterval);

        const baseline = calculateBaseline(samplesRef.current);
        console.log('[CalibrationScreen] Calibration complete. Baseline calculated:', baseline);
        onCalibrationComplete(baseline);
      }
    }, 200);

    return () => {
      clearInterval(sampleInterval);
    };
  }, [stream, detector, onCalibrationComplete]);

  const progress = Math.min(100, Math.round(((30 - secondsRemaining) / 30) * 100));

  return (
    <div style={{ maxWidth: 640, margin: '20px auto', width: '100%' }}>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h1 style={{ fontSize: '1.4rem', color: '#0f172a' }}>Personal Baseline Calibration</h1>
          {isPractice && <span className="practice-badge">Practice Mode</span>}
        </div>

        <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: 16 }}>
          Custodian AI is learning your natural gaze range, head position, and camera angle for 30 seconds so later
          thresholds are fair and tailored specifically to your desk environment.
        </p>

        {/* Video Preview with Guide */}
        <div className="video-preview-wrapper" style={{ width: 360, height: 270, margin: '0 auto 16px' }}>
          <video
            ref={videoRef}
            className="video-element"
            muted
            playsInline
            autoPlay
          />
          <div className="face-guide-overlay" />
        </div>

        {/* Progress Bar & Countdown */}
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', fontWeight: 600, marginBottom: 6 }}>
            <span>Calibration Progress ({progress}%)</span>
            <span style={{ color: '#2563eb' }}>{secondsRemaining}s remaining</span>
          </div>
          <div style={{ width: '100%', height: 10, background: '#e2e8f0', borderRadius: 9999, overflow: 'hidden' }}>
            <div
              style={{
                width: `${progress}%`,
                height: '100%',
                background: '#2563eb',
                transition: 'width 0.2s linear',
              }}
            />
          </div>
        </div>

        {/* Live Feedback */}
        <div
          style={{
            padding: 12,
            background: currentSample?.face_present ? '#f0fdf4' : '#fffbeb',
            border: `1px solid ${currentSample?.face_present ? '#bbf7d0' : '#fde68a'}`,
            borderRadius: 6,
            textAlign: 'center',
            fontSize: '0.9rem',
            color: currentSample?.face_present ? '#15803d' : '#b45309',
            marginBottom: 16,
          }}
        >
          {feedback}
        </div>

        {/* Live Telemetry Data */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, fontSize: '0.8rem', textAlign: 'center', background: '#f8fafc', padding: 10, borderRadius: 6 }}>
          <div>
            <div style={{ color: '#64748b' }}>Samples</div>
            <div style={{ fontWeight: 700, color: '#0f172a' }}>{samplesCount}</div>
          </div>
          <div>
            <div style={{ color: '#64748b' }}>Head Yaw</div>
            <div style={{ fontWeight: 700, color: '#0f172a' }}>{currentSample?.head_yaw ? `${currentSample.head_yaw}°` : '0°'}</div>
          </div>
          <div>
            <div style={{ color: '#64748b' }}>Head Pitch</div>
            <div style={{ fontWeight: 700, color: '#0f172a' }}>{currentSample?.head_pitch ? `${currentSample.head_pitch}°` : '0°'}</div>
          </div>
          <div>
            <div style={{ color: '#64748b' }}>Gaze Dev</div>
            <div style={{ fontWeight: 700, color: '#0f172a' }}>{currentSample?.gaze_offset_x ?? '0.00'}</div>
          </div>
        </div>

        <div style={{ marginTop: 14, textAlign: 'center' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: '0.8rem', padding: '4px 12px', color: '#64748b' }}
            onClick={() => {
              isDoneRef.current = true;
              onCalibrationComplete(calculateBaseline(samplesRef.current));
            }}
          >
            Skip to Exam (Use Current Baseline)
          </button>
        </div>
      </div>
    </div>
  );
};
