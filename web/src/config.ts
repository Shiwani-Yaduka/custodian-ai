/**
 * Configuration for Custodian AI student web application.
 */

export const CONFIG = {
  CAPTURE_DETECT_URL: import.meta.env.VITE_CAPTURE_DETECT_URL || 'http://127.0.0.1:8001',
  RISK_ENGINE_URL: import.meta.env.VITE_RISK_ENGINE_URL || 'http://127.0.0.1:8002',
  INVESTIGATOR_URL: import.meta.env.VITE_INVESTIGATOR_URL || 'http://127.0.0.1:8003',
  WARN_ESCALATE_URL: import.meta.env.VITE_WARN_ESCALATE_URL || 'http://127.0.0.1:8004',
  REVIEW_REPORT_URL: import.meta.env.VITE_REVIEW_REPORT_URL || 'http://127.0.0.1:8005',
  FPS: 5,
  SAMPLE_INTERVAL_MS: 200, // 5 frames per second
  BATCH_INTERVAL_MS: 1000, // Send feature batch every 1s
  CALIBRATION_DURATION_SEC: 30,
};
