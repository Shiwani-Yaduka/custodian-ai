import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { ScenarioMeta, ScenarioResult, ScenarioStep } from '../types';

interface ScenarioPanelProps {
  isOpen: boolean;
  onClose: () => void;
  activeSessionId?: string;
}

export const ScenarioPanel: React.FC<ScenarioPanelProps> = ({
  isOpen,
  onClose,
  activeSessionId,
}) => {
  const [scenarios, setScenarios] = useState<ScenarioMeta[]>([]);
  const [runningId, setRunningId] = useState<string | null>(null);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [currentStep, setCurrentStep] = useState<ScenarioStep | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resetMessage, setResetMessage] = useState<string | null>(null);

  useEffect(() => {
    api.getScenarios()
      .then(setScenarios)
      .catch((err) => console.warn('Could not load scenario metadata:', err));
  }, []);

  // Keyboard shortcut: Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleRunScenario = async (scenarioId: string) => {
    setRunningId(scenarioId);
    setError(null);
    setResetMessage(null);
    try {
      const res = await api.runScenario(scenarioId, activeSessionId);
      setResult(res);
      if (res.steps && res.steps.length > 0) {
        setCurrentStep(res.steps[res.steps.length - 1]);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Scenario execution failed';
      setError(msg);
    } finally {
      setRunningId(null);
    }
  };

  const handleResetSession = async () => {
    const sid = activeSessionId || 'demo-active-session';
    await api.resetScenarioSession(sid);
    setResult(null);
    setCurrentStep(null);
    setResetMessage(`Session ${sid} reset to initial CLEAR state.`);
  };

  // Helper colors for tiers
  const getTierColor = (tier?: string) => {
    switch (tier?.toUpperCase()) {
      case 'HELD':
        return '#dc2626';
      case 'ELEVATED':
        return '#ea580c';
      case 'WARNED':
        return '#f59e0b';
      case 'WATCHING':
        return '#2563eb';
      default:
        return '#16a34a';
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.75)',
        backdropFilter: 'blur(3px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
        fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      }}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: 12,
          maxWidth: 960,
          width: '100%',
          maxHeight: '92vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: '#f8fafc',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span
                style={{
                  background: '#fef3c7',
                  color: '#92400e',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: 4,
                  border: '1px solid #fde68a',
                }}
              >
                DEMO MODE
              </span>
              <span
                style={{
                  background: '#dbeafe',
                  color: '#1e40af',
                  fontWeight: 700,
                  fontSize: '0.75rem',
                  padding: '2px 8px',
                  borderRadius: 4,
                  border: '1px solid #bfdbfe',
                }}
              >
                REAL PIPELINE EXECUTION
              </span>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0, color: '#0f172a' }}>
                Interactive Scenario Simulator
              </h2>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>
              Feeds real sensory batches into InProcessPipeline with fast-forwarded virtual time. Demonstrates Section 9 invariants.
            </p>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              onClick={handleResetSession}
              style={{
                background: '#f1f5f9',
                border: '1px solid #cbd5e1',
                padding: '6px 12px',
                borderRadius: 6,
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer',
                color: '#334155',
              }}
            >
              🔄 Reset Session
            </button>
            <button
              onClick={onClose}
              style={{
                background: 'transparent',
                border: 'none',
                fontSize: '1.4rem',
                cursor: 'pointer',
                color: '#64748b',
                padding: '0 6px',
              }}
            >
              ✕
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div style={{ padding: 20, overflowY: 'auto', flex: 1 }}>
          {error && (
            <div style={{ background: '#fee2e2', border: '1px solid #f87171', color: '#991b1b', padding: 10, borderRadius: 6, marginBottom: 14, fontSize: '0.85rem' }}>
              {error}
            </div>
          )}
          {resetMessage && (
            <div style={{ background: '#f0fdf4', border: '1px solid #86efac', color: '#166534', padding: 10, borderRadius: 6, marginBottom: 14, fontSize: '0.85rem' }}>
              {resetMessage}
            </div>
          )}

          {/* Scenario Buttons Grid */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              Select Scenario to Run
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
              {scenarios.map((sc) => (
                <button
                  key={sc.id}
                  onClick={() => handleRunScenario(sc.id)}
                  disabled={runningId !== null}
                  style={{
                    background: runningId === sc.id ? '#dbeafe' : result?.scenario_id === sc.id ? '#eff6ff' : '#ffffff',
                    border: `1.5px solid ${result?.scenario_id === sc.id ? '#2563eb' : '#cbd5e1'}`,
                    borderRadius: 8,
                    padding: '10px 12px',
                    textAlign: 'left',
                    cursor: runningId !== null ? 'not-allowed' : 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: '0.875rem', color: '#0f172a', marginBottom: 2 }}>
                    {sc.title}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#2563eb', fontWeight: 600, marginBottom: 4 }}>
                    Expected: {sc.expected}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b', lineHeight: 1.3 }}>
                    {sc.description}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Live Telemetry Visualization Panel */}
          {currentStep && (
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, background: '#f8fafc', marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#64748b', fontWeight: 700 }}>
                    Live Engine State
                  </span>
                  <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#0f172a' }}>
                    Risk Score: <span style={{ color: getTierColor(currentStep.current_tier) }}>{currentStep.risk_score.toFixed(1)} / 100</span>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Active Tier</div>
                    <span
                      style={{
                        background: getTierColor(currentStep.current_tier),
                        color: '#ffffff',
                        padding: '3px 10px',
                        borderRadius: 4,
                        fontWeight: 700,
                        fontSize: '0.85rem',
                      }}
                    >
                      {currentStep.current_tier}
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Candidate</div>
                    <span
                      style={{
                        background: '#e2e8f0',
                        color: '#334155',
                        padding: '3px 10px',
                        borderRadius: 4,
                        fontWeight: 600,
                        fontSize: '0.85rem',
                      }}
                    >
                      {currentStep.candidate_tier}
                    </span>
                  </div>
                </div>
              </div>

              {/* Channel Accumulator Bars (with 40.0 cap indicator) */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginBottom: 6 }}>
                  <span>Sensor Channels (Accumulator A_c, Capped at K_c = 40.0)</span>
                  <span style={{ color: '#b45309', fontWeight: 600 }}>Warned threshold: 45.0 (2 channels required)</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                  {['camera', 'microphone', 'exam_window', 'device'].map((ch) => {
                    const val = currentStep.channel_bars[ch] || 0.0;
                    const pct = Math.min(100, (val / 40.0) * 100);
                    return (
                      <div key={ch} style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 6, padding: 8 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: 4 }}>
                          <span style={{ fontWeight: 600, color: '#334155' }}>{ch.replace('_', ' ')}</span>
                          <span style={{ color: val > 2.0 ? '#2563eb' : '#94a3b8', fontWeight: 700 }}>{val.toFixed(1)} / 40</span>
                        </div>
                        <div style={{ background: '#f1f5f9', height: 8, borderRadius: 4, overflow: 'hidden' }}>
                          <div
                            style={{
                              background: val >= 40.0 ? '#dc2626' : val > 15 ? '#f59e0b' : '#3b82f6',
                              width: `${pct}%`,
                              height: '100%',
                              transition: 'width 0.2s',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Gate Checklist & Bayesian Posteriors */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 14 }}>
                {/* Gate Checklist */}
                <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 6, padding: 12 }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#334155', marginBottom: 8 }}>
                    Escalation Gate Verification (Section 5)
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, fontSize: '0.75rem' }}>
                    {Object.entries(currentStep.gate_checklist).map(([gateName, passed]) => (
                      <div key={gateName} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span>{passed ? '✅' : '❌'}</span>
                        <span style={{ color: passed ? '#166534' : '#64748b', fontWeight: passed ? 600 : 400 }}>
                          {gateName.replace(/_/g, ' ')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Open Case Bayesian Belief */}
                <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 6, padding: 12 }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#334155', marginBottom: 8 }}>
                    Investigator Hypothesis Belief P(H | E)
                  </div>
                  {currentStep.open_case_posterior ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {Object.entries(currentStep.open_case_posterior).map(([hyp, prob]) => (
                        <div key={hyp} style={{ fontSize: '0.75rem' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                            <span style={{ fontWeight: 600 }}>{hyp}</span>
                            <span style={{ fontWeight: 700 }}>{(prob * 100).toFixed(1)}%</span>
                          </div>
                          <div style={{ background: '#f1f5f9', height: 6, borderRadius: 3, overflow: 'hidden' }}>
                            <div
                              style={{
                                background: hyp === 'deliberate' ? '#dc2626' : hyp === 'technical' ? '#16a34a' : '#3b82f6',
                                width: `${prob * 100}%`,
                                height: '100%',
                              }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ color: '#94a3b8', fontSize: '0.75rem', fontStyle: 'italic', padding: '10px 0' }}>
                      No active case open. Confidence above threshold or weight unescalated.
                    </div>
                  )}
                </div>
              </div>

              {/* Warning or Notice */}
              {currentStep.warning_issued && (
                <div style={{ marginTop: 12, background: '#fffbeb', border: '1px solid #fde68a', color: '#92400e', padding: '8px 12px', borderRadius: 6, fontSize: '0.8rem' }}>
                  🔔 <strong>Issued Notice:</strong> {currentStep.warning_issued}
                </div>
              )}
            </div>
          )}

          {/* Scenario Result Summary */}
          {result && (
            <div
              style={{
                background: result.passed ? '#f0fdf4' : '#fef2f2',
                border: `1.5px solid ${result.passed ? '#86efac' : '#fca5a5'}`,
                borderRadius: 8,
                padding: 14,
                marginBottom: 16,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                <span style={{ fontWeight: 700, fontSize: '0.9rem', color: result.passed ? '#166534' : '#991b1b' }}>
                  {result.passed ? '✅ Verification Passed' : '❌ Verification Failed'} — {result.title}
                </span>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>
                  Final Score: {result.final_score.toFixed(1)} · Tier: {result.final_tier}
                </span>
              </div>
              <div style={{ fontSize: '0.8rem', color: '#334155' }}>
                <div><strong>Expected:</strong> {result.expected_outcome}</div>
                <div style={{ marginTop: 2 }}><strong>Actual:</strong> {result.actual_outcome}</div>
              </div>
              {result.system_notice && (
                <div style={{ marginTop: 8, fontWeight: 600, fontSize: '0.8rem', color: '#b45309' }}>
                  📢 System Notice: {result.system_notice}
                </div>
              )}
            </div>
          )}

          {/* Execution Trace Steps */}
          {result && result.steps && result.steps.length > 0 && (
            <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 14 }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155', marginBottom: 8 }}>
                Fast-Forwarded Execution Timeline ({result.steps.length} snapshots)
              </div>
              <div style={{ maxHeight: 180, overflowY: 'auto', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ background: '#f8fafc', color: '#64748b', textAlign: 'left', borderBottom: '1px solid #e2e8f0' }}>
                      <th style={{ padding: '4px 6px' }}>Elapsed</th>
                      <th style={{ padding: '4px 6px' }}>Action</th>
                      <th style={{ padding: '4px 6px' }}>Score</th>
                      <th style={{ padding: '4px 6px' }}>Tier</th>
                      <th style={{ padding: '4px 6px' }}>Channels</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.steps.map((st, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                        <td style={{ padding: '4px 6px', color: '#64748b' }}>+{st.elapsed_seconds.toFixed(0)}s</td>
                        <td style={{ padding: '4px 6px', color: '#1e293b' }}>{st.description}</td>
                        <td style={{ padding: '4px 6px', fontWeight: 700 }}>{st.risk_score.toFixed(1)}</td>
                        <td style={{ padding: '4px 6px' }}>{st.current_tier}</td>
                        <td style={{ padding: '4px 6px', color: '#475569' }}>{st.active_channels_count} active</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
