import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { StudentTimelineItem } from '../types';

interface EvidenceRecordModalProps {
  sessionId: string;
  isPractice: boolean;
  onClose: () => void;
}

export const EvidenceRecordModal: React.FC<EvidenceRecordModalProps> = ({
  sessionId,
  isPractice,
  onClose,
}) => {
  const [timeline, setTimeline] = useState<StudentTimelineItem[]>([]);
  const [summary, setSummary] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (isPractice) {
      setLoading(false);
      setSummary('PRACTICE MODE: All sensory telemetry was processed locally in your browser. No exam records or penalties were recorded.');
      setTimeline([
        {
          timestamp: new Date().toLocaleTimeString(),
          elapsed_seconds: 0,
          type: 'calibration_completed',
          title: 'Practice Baseline Calibrated',
          description: 'Personal baseline geometry was computed locally without network transmission.',
          severity: 'info',
        },
      ]);
      return;
    }

    api
      .getStudentRecord(sessionId)
      .then((data: any) => {
        const rawEvents = [...(data.events || []), ...(data.observations || [])];
        if (data.timeline && Array.isArray(data.timeline) && rawEvents.length === 0) {
          rawEvents.push(...data.timeline);
        }

        rawEvents.sort((a: any, b: any) => (a.timestamp || 0) - (b.timestamp || 0));

        const formatted = rawEvents.map((ev: any) => {
          const tsStr =
            typeof ev.timestamp === 'number'
              ? new Date(ev.timestamp * 1000).toLocaleTimeString()
              : String(ev.timestamp || '');
          let title = ev.title;
          if (!title) {
            if (ev.event_type === 'notice') title = 'Official Notice';
            else if (ev.event_type === 'explanation') title = 'Student Explanation';
            else if (ev.event_type === 'status_change') title = 'Session Status';
            else if (ev.event_type === 'observation') title = 'Sensory Observation';
            else title = 'Ledger Event';
          }
          return {
            title,
            timestamp: tsStr,
            elapsed_seconds: 0,
            type: ev.event_type || 'info',
            description: ev.description,
            severity: ev.severity || (ev.event_type === 'notice' ? 'warning' : 'info'),
          } as StudentTimelineItem;
        });

        setTimeline(formatted);
        setSummary(data.summary || data.plain_text_summary || 'No notices recorded.');
      })
      .catch((err) => {
        console.error('Failed to load student record:', err);
        setSummary('Unable to load evidence record from server.');
      })
      .finally(() => setLoading(false));
  }, [sessionId, isPractice]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        background: 'rgba(15, 23, 42, 0.6)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 2000,
        padding: 20,
      }}
    >
      <div
        className="card"
        style={{
          maxWidth: 700,
          width: '100%',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          margin: 0,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: 12, marginBottom: 16 }}>
          <h2 style={{ fontSize: '1.25rem', color: '#0f172a' }}>My Evidence Record</h2>
          <button type="button" className="btn btn-secondary" style={{ padding: '4px 12px' }} onClick={onClose}>
            ✕ Close
          </button>
        </div>

        <div style={{ overflowY: 'auto', flex: 1, paddingRight: 8 }}>
          {loading ? (
            <p style={{ textAlign: 'center', color: '#64748b', padding: 20 }}>Loading your verified record...</p>
          ) : (
            <>
              <div style={{ background: '#f8fafc', padding: 14, borderRadius: 6, marginBottom: 16, fontSize: '0.9rem', color: '#334155', border: '1px solid #e2e8f0', whiteSpace: 'pre-line' }}>
                {summary}
              </div>

              <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 12, color: '#1e293b' }}>
                Chronological Event Timeline
              </h3>

              {timeline.length === 0 ? (
                <p style={{ color: '#64748b', fontSize: '0.9rem' }}>No anomalies or warnings have been recorded.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {timeline.map((item, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: 12,
                        borderRadius: 6,
                        border: '1px solid #e2e8f0',
                        background:
                          item.severity === 'alert'
                            ? '#fef2f2'
                            : item.severity === 'warning'
                            ? '#fffbeb'
                            : '#ffffff',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: '#64748b', marginBottom: 4 }}>
                        <span style={{ fontWeight: 600, color: '#1e293b' }}>{item.title}</span>
                        <span>{item.timestamp}</span>
                      </div>
                      <p style={{ fontSize: '0.88rem', color: '#334155' }}>{item.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 12, marginTop: 16, textAlign: 'right' }}>
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Return to Exam
          </button>
        </div>
      </div>
    </div>
  );
};
