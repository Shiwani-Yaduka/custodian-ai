import React, { useEffect, useState } from 'react';
import { api } from '../api';
import {
  FacultyCaseDetail,
  FacultyRiskPoint,
  FacultyTimeline,
  HeldSessionItem,
  MassFlagStatus,
  UserSession,
} from '../types';

interface FacultyPortalProps {
  session: UserSession;
  onSignOut: () => void;
  onOpenDemo?: () => void;
}

export const FacultyPortal: React.FC<FacultyPortalProps> = ({
  session,
  onSignOut,
  onOpenDemo,
}) => {
  const [heldSessions, setHeldSessions] = useState<HeldSessionItem[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [timeline, setTimeline] = useState<FacultyTimeline | null>(null);
  const [massFlag, setMassFlag] = useState<MassFlagStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Decision form state
  const [verdict, setVerdict] = useState<string>('cleared');
  const [notes, setNotes] = useState<string>('');
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);
  const [decisionSuccess, setDecisionSuccess] = useState<string | null>(null);

  // Load held sessions & mass flag state
  const loadHeldSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionsData, flagData] = await Promise.all([
        api.getHeldSessions(session.token),
        api.getMassFlagStatus().catch(() => null),
      ]);
      setHeldSessions(sessionsData);
      setMassFlag(flagData);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load held sessions';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHeldSessions();
  }, [session.token]);

  // Load detail when a session is selected
  useEffect(() => {
    if (!selectedSessionId) {
      setTimeline(null);
      return;
    }
    const loadDetail = async () => {
      setDetailLoading(true);
      setError(null);
      setDecisionSuccess(null);
      try {
        const data = await api.getFacultySessionDetail(session.token, selectedSessionId);
        setTimeline(data);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load session details';
        setError(msg);
      } finally {
        setDetailLoading(false);
      }
    };
    loadDetail();
  }, [selectedSessionId, session.token]);

  const handleSubmitDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSessionId) return;

    setSubmittingDecision(true);
    setDecisionSuccess(null);
    try {
      await api.submitFacultyDecision(session.token, selectedSessionId, verdict, notes);
      setDecisionSuccess(`Official determination recorded: ${verdict.toUpperCase().replace('_', ' ')}`);
      // Reload timeline and session list
      const updated = await api.getFacultySessionDetail(session.token, selectedSessionId);
      setTimeline(updated);
      const updatedList = await api.getHeldSessions(session.token);
      setHeldSessions(updatedList);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record decision';
      setError(msg);
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleDownloadReport = () => {
    if (!selectedSessionId) return;
    const reportUrl = api.getFacultyReportHtmlUrl(selectedSessionId);
    window.open(reportUrl, '_blank');
  };

  const formatTime = (ts?: number) => {
    if (!ts) return 'N/A';
    try {
      return new Date(ts * 1000).toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return String(ts);
    }
  };

  // Render SVG Risk Chart
  const renderRiskChart = (points: FacultyRiskPoint[]) => {
    if (!points || points.length === 0) {
      return (
        <div style={{ color: '#64748b', fontStyle: 'italic', padding: '24px 0', textAlign: 'center' }}>
          No risk score points recorded yet.
        </div>
      );
    }

    const svgWidth = 720;
    const svgHeight = 220;
    const padding = { top: 20, right: 30, bottom: 35, left: 45 };
    const chartW = svgWidth - padding.left - padding.right;
    const chartH = svgHeight - padding.top - padding.bottom;

    const minTs = points[0].timestamp;
    const maxTs = Math.max(points[points.length - 1].timestamp, minTs + 1.0);
    const tsRange = Math.max(maxTs - minTs, 1.0);

    const getX = (ts: number) => padding.left + ((ts - minTs) / tsRange) * chartW;
    const getY = (score: number) => padding.top + (1 - Math.min(100, Math.max(0, score)) / 100) * chartH;

    // Build SVG path
    let pathD = '';
    points.forEach((p, idx) => {
      const x = getX(p.timestamp);
      const y = getY(p.score);
      pathD += idx === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`;
    });

    const warnedY = getY(45);
    const elevatedY = getY(65);
    const heldY = getY(80);

    return (
      <div style={{ width: '100%', overflowX: 'auto', background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 12 }}>
        <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} style={{ width: '100%', height: 'auto', display: 'block' }}>
          {/* Threshold reference lines */}
          <line x1={padding.left} y1={warnedY} x2={svgWidth - padding.right} y2={warnedY} stroke="#f59e0b" strokeDasharray="4 4" strokeWidth="1.5" />
          <text x={svgWidth - padding.right - 4} y={warnedY - 4} textAnchor="end" fill="#b45309" fontSize="10" fontWeight="bold">WARNED (45)</text>

          <line x1={padding.left} y1={elevatedY} x2={svgWidth - padding.right} y2={elevatedY} stroke="#ea580c" strokeDasharray="4 4" strokeWidth="1.5" />
          <text x={svgWidth - padding.right - 4} y={elevatedY - 4} textAnchor="end" fill="#c2410c" fontSize="10" fontWeight="bold">ELEVATED (65)</text>

          <line x1={padding.left} y1={heldY} x2={svgWidth - padding.right} y2={heldY} stroke="#dc2626" strokeDasharray="4 4" strokeWidth="1.5" />
          <text x={svgWidth - padding.right - 4} y={heldY - 4} textAnchor="end" fill="#b91c1c" fontSize="10" fontWeight="bold">HELD (80)</text>

          {/* Grid Axes */}
          <line x1={padding.left} y1={padding.top} x2={padding.left} y2={svgHeight - padding.bottom} stroke="#cbd5e1" strokeWidth="1" />
          <line x1={padding.left} y1={svgHeight - padding.bottom} x2={svgWidth - padding.right} y2={svgHeight - padding.bottom} stroke="#cbd5e1" strokeWidth="1" />

          {/* Y Axis ticks */}
          {[0, 25, 50, 75, 100].map((val) => (
            <g key={val}>
              <text x={padding.left - 8} y={getY(val) + 3} textAnchor="end" fill="#64748b" fontSize="10">
                {val}
              </text>
              <line x1={padding.left - 4} y1={getY(val)} x2={padding.left} y2={getY(val)} stroke="#94a3b8" />
            </g>
          ))}

          {/* Risk Line */}
          {points.length > 1 && (
            <path d={pathD} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          )}

          {/* Points */}
          {points.map((p, idx) => {
            const cx = getX(p.timestamp);
            const cy = getY(p.score);
            const isHigh = p.score >= 80;
            return (
              <g key={idx}>
                <circle
                  cx={cx}
                  cy={cy}
                  r={isHigh ? 5 : 3.5}
                  fill={isHigh ? '#dc2626' : p.score >= 45 ? '#f59e0b' : '#2563eb'}
                  stroke="#ffffff"
                  strokeWidth="1.5"
                />
              </g>
            );
          })}

          <text x={svgWidth / 2} y={svgHeight - 8} textAnchor="middle" fill="#64748b" fontSize="11">
            Elapsed Virtual Time (Chronological)
          </text>
        </svg>
      </div>
    );
  };

  return (
    <div style={{ maxWidth: 1080, margin: '24px auto', padding: '0 16px', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, margin: '0 0 4px 0', color: '#0f172a' }}>
            Faculty Review Portal
          </h1>
          <div style={{ fontSize: '0.9rem', color: '#64748b' }}>
            Custodian AI · Reviewing held sessions under human sovereignty · Logged in as <strong>{session.username}</strong>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {onOpenDemo && (
            <button
              onClick={onOpenDemo}
              style={{
                background: '#e0e7ff',
                color: '#3730a3',
                border: '1px solid #c7d2fe',
                padding: '8px 14px',
                borderRadius: 6,
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              🧪 Demo Scenarios [D]
            </button>
          )}
          <button
            onClick={onSignOut}
            style={{
              background: '#f1f5f9',
              color: '#334155',
              border: '1px solid #cbd5e1',
              padding: '8px 14px',
              borderRadius: 6,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Mass-Flag Emergency Notification Banner */}
      {massFlag && massFlag.triggered && (
        <div
          style={{
            background: '#fef2f2',
            border: '2px solid #ef4444',
            borderRadius: 8,
            padding: '14px 18px',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            color: '#991b1b',
          }}
        >
          <span style={{ fontSize: '1.5rem' }}>🚨</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>
              Mass-Flag Infrastructure Alert Active
            </div>
            <div style={{ fontSize: '0.85rem' }}>
              Notice: <strong>"{massFlag.notice}"</strong> · Grace windows automatically relaxed by {massFlag.relaxation_factor}x.
              Check campus network connectivity before penalizing students.
            </div>
          </div>
        </div>
      )}

      {error && (
        <div style={{ background: '#fee2e2', border: '1px solid #f87171', color: '#991b1b', padding: 12, borderRadius: 6, marginBottom: 16 }}>
          {error}
        </div>
      )}

      {/* Main View: Session List vs Selected Session Detail */}
      {!selectedSessionId ? (
        <div style={{ background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 24, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600, margin: 0, color: '#1e293b' }}>
                Held Sessions Awaiting Review ({heldSessions.length})
              </h2>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.875rem', color: '#64748b' }}>
                Only sessions reaching the HELD tier (multi-channel corroborated) are queued for faculty adjudication.
              </p>
            </div>
            <button
              onClick={loadHeldSessions}
              style={{
                background: '#f8fafc',
                border: '1px solid #cbd5e1',
                padding: '6px 12px',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: '0.85rem',
              }}
            >
              🔄 Refresh Queue
            </button>
          </div>

          {loading ? (
            <div style={{ padding: '32px 0', textAlign: 'center', color: '#64748b' }}>Loading held sessions...</div>
          ) : heldSessions.length === 0 ? (
            <div style={{ padding: '40px 0', textAlign: 'center', background: '#f8fafc', borderRadius: 6, border: '1px dashed #cbd5e1' }}>
              <div style={{ fontSize: '2rem', marginBottom: 8 }}>✅</div>
              <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: 4 }}>Queue Clean — No Held Sessions</div>
              <div style={{ fontSize: '0.875rem', color: '#64748b', maxWidth: 460, margin: '0 auto 16px auto' }}>
                All student sessions are either operating normally in CLEAR/WATCHING, or have already been resolved.
              </div>
              {onOpenDemo && (
                <button
                  onClick={onOpenDemo}
                  style={{
                    background: '#2563eb',
                    color: '#ffffff',
                    border: 'none',
                    padding: '8px 16px',
                    borderRadius: 6,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Run "Phone + Notes" Corroborated Demo Scenario
                </button>
              )}
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ background: '#f8fafc', borderBottom: '2px solid #e2e8f0', textAlign: 'left', fontSize: '0.85rem', color: '#475569' }}>
                    <th style={{ padding: '10px 12px' }}>Session ID</th>
                    <th style={{ padding: '10px 12px' }}>Paused At</th>
                    <th style={{ padding: '10px 12px' }}>Evidence Summary</th>
                    <th style={{ padding: '10px 12px' }}>Status</th>
                    <th style={{ padding: '10px 12px', textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {heldSessions.map((sess) => (
                    <tr key={sess.session_id} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '12px', fontFamily: 'monospace', fontWeight: 600, fontSize: '0.9rem' }}>
                        {sess.session_id}
                      </td>
                      <td style={{ padding: '12px', fontSize: '0.875rem', color: '#64748b' }}>
                        {formatTime(sess.paused_at)}
                      </td>
                      <td style={{ padding: '12px', fontSize: '0.875rem', color: '#334155', maxWidth: 360 }}>
                        {sess.evidence_summary}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span
                          style={{
                            background: sess.status === 'held' ? '#fee2e2' : '#e0e7ff',
                            color: sess.status === 'held' ? '#991b1b' : '#3730a3',
                            padding: '3px 8px',
                            borderRadius: 4,
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            textTransform: 'uppercase',
                          }}
                        >
                          {sess.status}
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <button
                          onClick={() => setSelectedSessionId(sess.session_id)}
                          style={{
                            background: '#2563eb',
                            color: '#ffffff',
                            border: 'none',
                            padding: '6px 14px',
                            borderRadius: 6,
                            fontSize: '0.85rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                          }}
                        >
                          Inspect & Decide →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Detailed Session Review */
        <div>
          <button
            onClick={() => setSelectedSessionId(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#2563eb',
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              marginBottom: 16,
              padding: 0,
            }}
          >
            ← Back to Held Queue
          </button>

          {detailLoading || !timeline ? (
            <div style={{ background: '#ffffff', borderRadius: 8, padding: 32, textAlign: 'center', color: '#64748b' }}>
              Loading audit timeline for {selectedSessionId}...
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 20 }}>
              {/* Header Overview Card */}
              <div style={{ background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20, boxShadow: '0 1px 3px rgba(0,0,0,0.05)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                      <h2 style={{ fontSize: '1.35rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                        Session: {timeline.session_id}
                      </h2>
                      <span
                        style={{
                          background: timeline.status === 'held' ? '#dc2626' : '#16a34a',
                          color: '#ffffff',
                          padding: '3px 10px',
                          borderRadius: 4,
                          fontWeight: 700,
                          fontSize: '0.8rem',
                          textTransform: 'uppercase',
                        }}
                      >
                        {timeline.status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.875rem', color: '#64748b' }}>
                      Peak Risk Score: <strong style={{ color: '#dc2626' }}>{timeline.peak_risk_score.toFixed(1)} / 100</strong> · Started: {formatTime(timeline.start_time)}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: 10 }}>
                    <button
                      onClick={handleDownloadReport}
                      style={{
                        background: '#0f172a',
                        color: '#ffffff',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: 6,
                        fontWeight: 600,
                        fontSize: '0.875rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      📄 Download Official Audit Report (HTML)
                    </button>
                  </div>
                </div>

                {timeline.hold_summary && (
                  <div style={{ background: '#fef2f2', borderLeft: '4px solid #ef4444', padding: '10px 14px', borderRadius: 4, marginTop: 16, color: '#991b1b', fontSize: '0.875rem' }}>
                    <strong>Hold Reason:</strong> {timeline.hold_summary}
                  </div>
                )}
              </div>

              {/* Visual Risk-Over-Time Chart */}
              <div style={{ background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20 }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 12px 0', color: '#1e293b' }}>
                  Risk Score Progression Over Time
                </h3>
                {renderRiskChart(timeline.risk_points)}
              </div>

              {/* Investigator Reasoning & Bayesian Probes */}
              <div style={{ background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20 }}>
                <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 12px 0', color: '#1e293b' }}>
                  Investigator Agent Reasoning & Bayesian Probes
                </h3>
                {timeline.investigation_cases.length === 0 ? (
                  <div style={{ color: '#64748b', fontSize: '0.875rem' }}>No investigation cases opened for this session.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {timeline.investigation_cases.map((c: FacultyCaseDetail) => (
                      <div key={c.case_id} style={{ border: '1px solid #e2e8f0', borderRadius: 6, padding: 14, background: '#f8fafc' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>
                            Case {c.case_id}: {c.open_reason}
                          </span>
                          <span style={{ background: '#e0e7ff', color: '#3730a3', padding: '2px 8px', borderRadius: 4, fontSize: '0.75rem', fontWeight: 700 }}>
                            {c.resolution ? c.resolution.toUpperCase() : 'PENDING'} ({c.multiplier}x multiplier)
                          </span>
                        </div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: 8 }}>
                          Probes Executed: {c.probes.length}
                        </div>
                        {c.probes.length > 0 && (
                          <div style={{ background: '#ffffff', borderRadius: 4, border: '1px solid #e2e8f0', padding: 8 }}>
                            {c.probes.map((p, idx) => (
                              <div key={idx} style={{ fontSize: '0.8rem', padding: '4px 0', borderBottom: idx < c.probes.length - 1 ? '1px solid #f1f5f9' : 'none', display: 'flex', justifyContent: 'space-between' }}>
                                <span><strong>{p.probe_name}</strong> → {p.outcome}</span>
                                <span style={{ color: '#64748b' }}>cost {p.cost}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Student Explanations & Stub Clip Markers */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
                {/* Student's Own Explanation */}
                <div style={{ background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20 }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 12px 0', color: '#1e293b' }}>
                    Student Statement / Explanations
                  </h3>
                  {timeline.student_explanations.length === 0 ? (
                    <div style={{ color: '#64748b', fontSize: '0.875rem', fontStyle: 'italic' }}>
                      No explanation was submitted by the candidate during the exam.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {timeline.student_explanations.map((exp, idx) => (
                        <div key={idx} style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 6, padding: 12 }}>
                          <div style={{ fontSize: '0.75rem', color: '#1e40af', marginBottom: 4 }}>
                            Submitted at {formatTime(exp.submitted_at)}
                          </div>
                          <div style={{ fontSize: '0.875rem', color: '#1e3a8a', fontStyle: 'italic' }}>
                            "{exp.explanation_text}"
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Evidence Stub Clip Marker */}
                <div style={{ background: '#ffffff', borderRadius: 8, border: '1px solid #e2e8f0', padding: 20 }}>
                  <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 12px 0', color: '#1e293b' }}>
                    Video Audit Stub Clips
                  </h3>
                  <div style={{ fontSize: '0.85rem', color: '#475569', marginBottom: 12 }}>
                    In accordance with Section 7 privacy rules, full video is never stored. A 10-second stub record marks the incident boundary for audit verification:
                  </div>
                  <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, padding: 12, fontFamily: 'monospace', fontSize: '0.85rem', color: '#334155' }}>
                    <div><strong>Marker:</strong> stub-clip-{timeline.session_id}</div>
                    <div style={{ marginTop: 4 }}><strong>Duration:</strong> 10.0s around escalation threshold</div>
                    <div style={{ marginTop: 4 }}><strong>Resolution:</strong> 640x480 telemetry reference</div>
                  </div>
                </div>
              </div>

              {/* Faculty Human Decision Form */}
              <div style={{ background: '#ffffff', borderRadius: 8, border: '2px solid #2563eb', padding: 24 }}>
                <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 8px 0', color: '#0f172a' }}>
                  Record Official Faculty Determination
                </h3>
                <p style={{ fontSize: '0.875rem', color: '#64748b', margin: '0 0 16px 0' }}>
                  All punitive decisions must be made by human faculty. Select the determination and enter supporting review comments.
                </p>

                {decisionSuccess && (
                  <div style={{ background: '#f0fdf4', border: '1px solid #86efac', color: '#166534', padding: 12, borderRadius: 6, marginBottom: 16 }}>
                    ✅ {decisionSuccess}
                  </div>
                )}

                <form onSubmit={handleSubmitDecision}>
                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: 8, color: '#334155' }}>
                      Adjudication Verdict:
                    </label>
                    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                      {[
                        { id: 'cleared', label: 'Cleared (No Violation)', desc: 'Release hold; exam is valid' },
                        { id: 'warning_stands', label: 'Warning Stands', desc: 'Hold stands; record on ledger' },
                        { id: 'refer_onward', label: 'Refer Onward', desc: 'Escalate to Academic Integrity Board' },
                      ].map((opt) => (
                        <label
                          key={opt.id}
                          style={{
                            flex: '1 1 200px',
                            border: `2px solid ${verdict === opt.id ? '#2563eb' : '#cbd5e1'}`,
                            borderRadius: 6,
                            padding: '10px 14px',
                            cursor: 'pointer',
                            background: verdict === opt.id ? '#eff6ff' : '#ffffff',
                          }}
                        >
                          <input
                            type="radio"
                            name="verdict"
                            value={opt.id}
                            checked={verdict === opt.id}
                            onChange={(e) => setVerdict(e.target.value)}
                            style={{ marginRight: 8 }}
                          />
                          <span style={{ fontWeight: 600, fontSize: '0.9rem', color: '#0f172a' }}>{opt.label}</span>
                          <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 2 }}>{opt.desc}</div>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginBottom: 16 }}>
                    <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: 6, color: '#334155' }}>
                      Faculty Review Comments:
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      placeholder="Enter rationales, evidence notes, or instructions for the student record..."
                      rows={3}
                      style={{
                        width: '100%',
                        padding: 10,
                        borderRadius: 6,
                        border: '1px solid #cbd5e1',
                        fontSize: '0.875rem',
                        boxSizing: 'border-box',
                      }}
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={submittingDecision}
                    style={{
                      background: '#2563eb',
                      color: '#ffffff',
                      border: 'none',
                      padding: '10px 20px',
                      borderRadius: 6,
                      fontWeight: 600,
                      fontSize: '0.9rem',
                      cursor: submittingDecision ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {submittingDecision ? 'Recording Decision...' : 'Submit Official Determination'}
                  </button>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
