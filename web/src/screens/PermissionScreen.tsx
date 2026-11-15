import React, { useEffect, useRef, useState } from 'react';
import { FaceDetector } from '../detection/faceLandmarker';

interface PermissionScreenProps {
  onPermissionGranted: (stream: MediaStream, detector: FaceDetector) => void;
  onBack: () => void;
}

export const PermissionScreen: React.FC<PermissionScreenProps> = ({ onPermissionGranted, onBack }) => {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [detector, setDetector] = useState<FaceDetector | null>(null);
  const [detectorReady, setDetectorReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    // Initialize offline MediaPipe Face Landmarker in background
    const det = new FaceDetector();
    det
      .initialize()
      .then(() => {
        setDetector(det);
        setDetectorReady(true);
      })
      .catch((err) => {
        console.error('Detector init failed:', err);
        setError('Failed to load local MediaPipe vision model. Please check browser WebAssembly support.');
      });

    return () => {
      // Don't close detector here if passing forward
    };
  }, []);

  const requestHardwarePermissions = async () => {
    setError(null);
    setLoading(true);

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Webcam and audio access is not supported in this browser or insecure context.');
      }

      const mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: true,
      });

      setStream(mediaStream);

      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        videoRef.current.play().catch(() => {});
      }
    } catch (err: unknown) {
      const e = err as { name?: string; message?: string };
      if (e.name === 'NotAllowedError' || e.name === 'PermissionDeniedError') {
        setError('Camera or Microphone access was denied. Please allow camera and microphone permissions in your browser URL bar.');
      } else if (e.name === 'NotFoundError' || e.name === 'DevicesNotFoundError') {
        setError('No camera or microphone hardware found on your device.');
      } else if (e.name === 'NotReadableError' || e.name === 'TrackStartError') {
        setError('Your camera or microphone is currently in use by another application.');
      } else {
        setError(e.message || 'Unable to access camera or microphone.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleProceed = () => {
    if (stream && detector && detectorReady) {
      onPermissionGranted(stream, detector);
    }
  };

  return (
    <div style={{ maxWidth: 640, margin: '20px auto', width: '100%' }}>
      <div className="card">
        <h1 style={{ fontSize: '1.5rem', marginBottom: 8, color: '#0f172a' }}>Camera & Microphone Setup</h1>
        <p style={{ color: '#64748b', fontSize: '0.95rem', marginBottom: 20 }}>
          Ensure your webcam and microphone are working. Only abstract measurements are collected locally.
        </p>

        {error && (
          <div
            role="alert"
            style={{
              background: '#fef2f2',
              color: '#b91c1c',
              border: '1px solid #fecaca',
              padding: 12,
              borderRadius: 6,
              marginBottom: 20,
              fontSize: '0.9rem',
            }}
          >
            <strong>Hardware Setup Error:</strong> {error}
          </div>
        )}

        <div className="video-preview-wrapper" style={{ width: 360, height: 270, margin: '0 auto 20px' }}>
          <video
            ref={videoRef}
            className="video-element"
            muted
            playsInline
            autoPlay
          />
          {!stream && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center',
                color: '#94a3b8',
                padding: 20,
                textAlign: 'center',
              }}
            >
              <div style={{ fontSize: '2rem', marginBottom: 8 }}>📷</div>
              <p style={{ fontSize: '0.9rem' }}>Camera preview will appear here</p>
            </div>
          )}
          {stream && <div className="face-guide-overlay" />}
        </div>

        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          {!stream ? (
            <button
              type="button"
              className="btn btn-primary"
              onClick={requestHardwarePermissions}
              disabled={loading}
            >
              {loading ? 'Requesting Access...' : 'Allow Camera & Microphone Access'}
            </button>
          ) : (
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, color: '#15803d', fontSize: '0.9rem', fontWeight: 600 }}>
              <span className="status-dot" /> Camera & Microphone Active · Mirror Feed Ready
            </div>
          )}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid #e2e8f0', paddingTop: 16 }}>
          <button type="button" className="btn btn-secondary" onClick={onBack}>
            Back
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!stream || !detectorReady}
            onClick={handleProceed}
          >
            {!detectorReady ? 'Loading Local ML Model...' : 'Start 30-Second Calibration'}
          </button>
        </div>
      </div>
    </div>
  );
};
