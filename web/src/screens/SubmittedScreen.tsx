import React, { useState } from 'react';
import { EvidenceRecordModal } from './EvidenceRecordModal';

interface SubmittedScreenProps {
  sessionId: string;
  isPractice: boolean;
  onSignOut: () => void;
}

export const SubmittedScreen: React.FC<SubmittedScreenProps> = ({
  sessionId,
  isPractice,
  onSignOut,
}) => {
  const [showEvidence, setShowEvidence] = useState(false);

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', width: '100%' }}>
      <div className="card" style={{ textAlign: 'center', padding: 36 }}>
        <div style={{ fontSize: '3rem', marginBottom: 12 }}>✓</div>
        <h1 style={{ fontSize: '1.6rem', color: '#15803d', marginBottom: 8 }}>
          {isPractice ? 'Practice Session Completed' : 'Exam Submitted Successfully'}
        </h1>
        <p style={{ color: '#475569', fontSize: '0.95rem', marginBottom: 24, lineHeight: 1.6 }}>
          {isPractice
            ? 'Your practice exam run is complete. All camera and audio feature processing was executed in-browser with zero recordings saved.'
            : 'Your exam answers have been securely recorded. All sensory data points have been archived into your transparent, append-only evidence record.'}
        </p>

        <div style={{ background: '#f8fafc', padding: 16, borderRadius: 8, marginBottom: 28, border: '1px solid #e2e8f0', textAlign: 'left' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.9rem' }}>
            <span style={{ color: '#64748b' }}>Session Reference:</span>
            <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{sessionId}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.9rem' }}>
            <span style={{ color: '#64748b' }}>Submission Time:</span>
            <span>{new Date().toLocaleTimeString()}</span>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
            <span style={{ color: '#64748b' }}>Academic Status:</span>
            <span style={{ color: '#15803d', fontWeight: 600 }}>Submitted for Faculty Review</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 12, justifyContent: 'center' }}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setShowEvidence(true)}
          >
            Inspect My Evidence Record
          </button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onSignOut}
          >
            Sign Out
          </button>
        </div>
      </div>

      {showEvidence && (
        <EvidenceRecordModal
          sessionId={sessionId}
          isPractice={isPractice}
          onClose={() => setShowEvidence(false)}
        />
      )}
    </div>
  );
};
