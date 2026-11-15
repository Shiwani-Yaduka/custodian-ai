import React, { useState } from 'react';

interface ConsentScreenProps {
  onConsentGiven: () => void;
  onBack: () => void;
}

export const ConsentScreen: React.FC<ConsentScreenProps> = ({ onConsentGiven, onBack }) => {
  const [agreed, setAgreed] = useState(false);

  return (
    <div style={{ maxWidth: 720, margin: '20px auto', width: '100%' }}>
      <div className="card">
        <h1 style={{ fontSize: '1.5rem', marginBottom: 8, color: '#0f172a' }}>Privacy Notice & Student Consent</h1>
        <p style={{ color: '#64748b', fontSize: '0.95rem', marginBottom: 20 }}>
          Please review how Custodian AI protects your personal privacy and academic rights.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: 16, borderRadius: 8 }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#166534', marginBottom: 8 }}>
              ✓ What is Measured (Locally in Browser)
            </h2>
            <ul style={{ fontSize: '0.88rem', color: '#15803d', paddingLeft: 18, lineHeight: 1.6 }}>
              <li>Abstract facial landmark geometry (head yaw, pitch, and relative gaze offset).</li>
              <li>Ambient volume level (energy level only).</li>
              <li>Exam window focus and browser tab visibility.</li>
              <li>Camera track status and measured frame rate.</li>
              <li>Your personal 30-second neutral calibration baseline.</li>
            </ul>
          </div>

          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', padding: 16, borderRadius: 8 }}>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#991b1b', marginBottom: 8 }}>
              ✗ What is NEVER Collected or Done
            </h2>
            <ul style={{ fontSize: '0.88rem', color: '#b91c1c', paddingLeft: 18, lineHeight: 1.6 }}>
              <li><strong>NO video or photo recordings</strong> leave your computer.</li>
              <li><strong>NO audio recordings</strong> or speech transcripts.</li>
              <li><strong>NO screen captures</strong> or keystroke logging.</li>
              <li><strong>NO automatic failing</strong> or grade penalties — only a human faculty member can make academic determinations.</li>
            </ul>
          </div>
        </div>

        <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', padding: 16, borderRadius: 8, marginBottom: 24 }}>
          <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#1e40af', marginBottom: 6 }}>
            Your Academic Rights & Due Process
          </h2>
          <p style={{ fontSize: '0.88rem', color: '#1d4ed8', lineHeight: 1.5 }}>
            You have the right to inspect your complete chronological evidence ledger at any point during and after the
            examination. If unusual anomalies occur (such as technical glitches or room interruptions), you can submit
            your explanation directly into the record.
          </p>
        </div>

        <div style={{ marginBottom: 24, padding: 12, background: '#f8fafc', borderRadius: 6 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer', fontSize: '0.95rem' }}>
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              style={{ width: 18, height: 18 }}
            />
            <span>
              I have read and understood the privacy protections and consent to calibrated sensory monitoring for this exam.
            </span>
          </label>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button type="button" className="btn btn-secondary" onClick={onBack}>
            Back
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={!agreed}
            onClick={onConsentGiven}
          >
            I Consent & Continue to Camera Setup
          </button>
        </div>
      </div>
    </div>
  );
};
