import React, { useEffect, useRef, useState } from 'react';
import { api, PendingProbe } from '../api';
import { SensorBatcher } from '../detection/batcher';
import { FaceDetector } from '../detection/faceLandmarker';
import { CalibrationBaseline, Exam, RawFaceSample } from '../types';
import { EvidenceRecordModal } from './EvidenceRecordModal';

interface ExamScreenProps {
  sessionId: string;
  stream: MediaStream;
  detector: FaceDetector;
  baseline: CalibrationBaseline;
  isPractice: boolean;
  onExamSubmitted: () => void;
}

// Fallback Demo Exam if backend /exams is not yet populated
const FALLBACK_EXAM: Exam = {
  id: 1,
  title: 'Demo Exam: Computer Science & Systems',
  description: '10 Multiple Choice Questions and 2 Written Response Questions. 30 Minutes.',
  duration_minutes: 30,
  questions: [
    {
      id: 'q1',
      type: 'mcq',
      prompt: 'Which data structure operates on a First-In, First-Out (FIFO) basis?',
      options: ['Stack', 'Queue', 'Binary Search Tree', 'Heap'],
    },
    {
      id: 'q2',
      type: 'mcq',
      prompt: 'What is the average-case time complexity of QuickSort?',
      options: ['O(n)', 'O(n log n)', 'O(n²)', 'O(1)'],
    },
    {
      id: 'q3',
      type: 'mcq',
      prompt: 'Which layer of the OSI model does the TCP protocol operate on?',
      options: ['Network Layer', 'Transport Layer', 'Data Link Layer', 'Application Layer'],
    },
    {
      id: 'q4',
      type: 'mcq',
      prompt: 'In SQL, which command is used to remove a table structure entirely?',
      options: ['DELETE', 'REMOVE', 'DROP', 'TRUNCATE'],
    },
    {
      id: 'q5',
      type: 'mcq',
      prompt: 'What is the primary purpose of a mutex in concurrent programming?',
      options: ['Data compression', 'Mutual exclusion for shared resources', 'Memory defragmentation', 'Network routing'],
    },
    {
      id: 'q6',
      type: 'mcq',
      prompt: 'Which HTTP status code signifies "Forbidden"?',
      options: ['401', '403', '404', '500'],
    },
    {
      id: 'q7',
      type: 'mcq',
      prompt: 'In Git, which command creates a new branch and switches to it in one step?',
      options: ['git branch -c', 'git checkout -b', 'git switch -m', 'git push -b'],
    },
    {
      id: 'q8',
      type: 'mcq',
      prompt: 'What is the main benefit of WebAssembly (WASM) in the browser?',
      options: ['Replaces HTML', 'Runs near-native speed code in sandboxed browser', 'Enables unrestricted hard drive access', 'Bypasses CORS restrictions'],
    },
    {
      id: 'q9',
      type: 'mcq',
      prompt: 'Which algorithmic paradigm does Dijkstra’s shortest path algorithm use?',
      options: ['Greedy', 'Divide and Conquer', 'Dynamic Programming', 'Backtracking'],
    },
    {
      id: 'q10',
      type: 'mcq',
      prompt: 'In relational databases, what does the ACID acronym stand for?',
      options: ['Atomicity, Consistency, Isolation, Durability', 'Accuracy, Concurrency, Integrity, Delivery', 'Authentication, Cipher, Identity, Defense', 'Array, Cache, Index, Document'],
    },
    {
      id: 'q11',
      type: 'written',
      prompt: 'Explain the difference between process concurrency and parallelism in operating systems.',
    },
    {
      id: 'q12',
      type: 'written',
      prompt: 'Why is client-side sensory feature extraction fundamentally more privacy-preserving than video streaming in remote proctoring?',
    },
  ],
};

export const ExamScreen: React.FC<ExamScreenProps> = ({
  sessionId,
  stream,
  detector,
  isPractice,
  onExamSubmitted,
}) => {
  const [exam, setExam] = useState<Exam>(FALLBACK_EXAM);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [secondsRemaining, setSecondsRemaining] = useState(30 * 60);
  const [isHeld, setIsHeld] = useState(false);
  const [timeAddedAlert, setTimeAddedAlert] = useState<string | null>(null);

  // Warning & Anomaly state
  const [activeWarning, setActiveWarning] = useState<string | null>(null);
  const [warningTier, setWarningTier] = useState<string>('CLEAR');
  const [explanationText, setExplanationText] = useState('');
  const [explanationStatus, setExplanationStatus] = useState<string | null>(null);

  // Soft reminder probe
  const [softReminder, setSoftReminder] = useState<string | null>(null);

  // Status indicators
  const [currentFps, setCurrentFps] = useState(5.0);
  const [audioLevel, setAudioLevel] = useState(0.0);
  const [facePresent, setFacePresent] = useState(true);
  const [showEvidence, setShowEvidence] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const batcherRef = useRef<SensorBatcher | null>(null);
  const latestSampleRef = useRef<RawFaceSample | null>(null);

  // 1. Initialize Exam Questions
  useEffect(() => {
    if (!isPractice) {
      api
        .getExams()
        .then((exams) => {
          if (exams && exams.length > 0) {
            setExam(exams[0]);
            setSecondsRemaining(exams[0].duration_minutes * 60);
          }
        })
        .catch((err) => {
          console.warn('[ExamScreen] Falling back to default Demo Exam:', err);
        });
    }
  }, [isPractice]);

  // 2. Start Video & In-Browser 5 FPS Detection Loop
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
      videoRef.current.play().catch(() => {});
    }

    // Initialize 1-second batcher
    const batcher = new SensorBatcher(sessionId, isPractice, {
      onAudioLevel: (lvl) => setAudioLevel(lvl),
      onFpsUpdated: (fps) => setCurrentFps(fps),
    });
    batcher.attachAudioStream(stream);
    batcher.start();
    batcherRef.current = batcher;

    // 5 FPS detection loop (every 200ms)
    const detectInterval = setInterval(() => {
      if (!videoRef.current) return;
      const sample = detector.processVideoFrame(videoRef.current, performance.now());
      latestSampleRef.current = sample;
      setFacePresent(sample.face_present);
      batcher.updateFaceSample(sample, stream.active);
    }, 200);

    return () => {
      clearInterval(detectInterval);
      batcher.stop();
    };
  }, [stream, detector, sessionId, isPractice]);

  // 3. Countdown Timer (decrements when not held)
  useEffect(() => {
    const timer = setInterval(() => {
      if (!isHeld) {
        setSecondsRemaining((prev) => Math.max(0, prev - 1));
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [isHeld]);

  // 4. Polling for Backend Status, Gating & Investigator Probes
  useEffect(() => {
    if (isPractice) return;

    const pollInterval = setInterval(async () => {
      // A. Check Risk & Gating State
      const state = await api.getRiskState(sessionId);
      if (state) {
        const tier = state.candidate_tier;
        setWarningTier(tier);

        if (tier === 'HELD') {
          setIsHeld(true);
          setActiveWarning(
            'Your exam has been paused and transferred to a human faculty member for review. Your answers are preserved.'
          );
        } else if (tier === 'ELEVATED') {
          setActiveWarning(
            'Second Notice: Repeated multi-channel anomalies observed. 10 minutes have been added to your exam clock.'
          );
          if (!timeAddedAlert) {
            setTimeAddedAlert('10 minutes added as time off the clock');
            setSecondsRemaining((prev) => prev + 10 * 60);
          }
        } else if (tier === 'WARNED') {
          setActiveWarning(
            'Notice: An unusual pattern of observations was detected. Please ensure you remain focused on your screen.'
          );
        } else {
          setActiveWarning(null);
        }
      }

      // B. Check Pending Probes from Investigator
      const probe: PendingProbe | null = await api.pollPendingProbes(sessionId);
      if (probe && probe.probe_name === 'soft_reminder') {
        setSoftReminder(probe.message || 'Gentle reminder: Please keep your attention focused on your exam screen.');

        // Observe student reaction over 5 seconds
        setTimeout(async () => {
          const sample = latestSampleRef.current;
          const isCentered = sample ? sample.face_present && Math.abs(sample.head_yaw) < 20 : true;
          const outcome = isCentered ? 'behavior_corrected' : 'behavior_continued';
          await api.respondToProbe(sessionId, 'soft_reminder', outcome);
          setSoftReminder(null);
        }, 5000);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [sessionId, isPractice, timeAddedAlert]);

  const handleAnswerChange = (questionId: string, answer: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: answer }));
  };

  const handleExplanationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!explanationText.trim()) return;

    setExplanationStatus('Submitting explanation...');
    if (isPractice) {
      setExplanationStatus('✓ Explanation recorded in practice log.');
      setExplanationText('');
      setTimeout(() => setExplanationStatus(null), 3000);
      return;
    }

    try {
      await api.submitExplanation(sessionId, explanationText);
      setExplanationStatus('✓ Explanation successfully recorded to your immutable evidence ledger.');
      setExplanationText('');
      setTimeout(() => setExplanationStatus(null), 4000);
    } catch (err) {
      console.error('Explanation submission error:', err);
      setExplanationStatus('Failed to submit explanation. Please retry.');
    }
  };

  const formatTimer = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="app-container">
      {/* Header with Title, Status Badges & Timer */}
      <header className="app-header">
        <div className="app-title">
          <span>Custodian AI</span>
          {isPractice ? (
            <span className="practice-badge">Practice Mode (No Penalty)</span>
          ) : (
            <span style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 500 }}>
              Session: <code style={{ fontFamily: 'monospace' }}>{sessionId}</code>
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Status Badge */}
          <div className="status-badge">
            <span
              className={`status-dot ${
                warningTier === 'HELD' ? 'alert' : warningTier === 'WARNED' || warningTier === 'ELEVATED' ? 'warning' : ''
              }`}
            />
            <span>
              {facePresent ? 'Monitoring Active' : 'Face Missing'} · Audio {audioLevel > 0.05 ? 'Active' : 'Quiet'} · {currentFps} fps
            </span>
          </div>

          {/* Exam Timer */}
          <div
            style={{
              padding: '6px 14px',
              borderRadius: 6,
              background: isHeld ? '#fef2f2' : '#f1f5f9',
              color: isHeld ? '#b91c1c' : '#0f172a',
              fontWeight: 700,
              fontSize: '1rem',
              fontFamily: 'monospace',
              border: '1px solid #cbd5e1',
            }}
          >
            ⏱ {formatTimer(secondsRemaining)}
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            style={{ fontSize: '0.85rem', padding: '6px 12px' }}
            onClick={() => setShowEvidence(true)}
          >
            My Evidence Record
          </button>
        </div>
      </header>

      {/* Soft Reminder Toast */}
      {softReminder && (
        <div className="soft-reminder-toast" role="status">
          <span>ℹ️</span>
          <span>{softReminder}</span>
        </div>
      )}

      {/* Main Content Layout */}
      <main className="main-content">
        {/* Warning Banner */}
        {activeWarning && (
          <div className="warning-banner" role="alert">
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
              <span>⚠️</span>
              <span>{activeWarning}</span>
            </div>
            <p style={{ fontSize: '0.88rem' }}>
              Custodian AI treats observations as evidence under uncertainty. If there is a reason for this occurrence
              (such as an unexpected noise or technical glitch), you may submit an explanation below.
            </p>
          </div>
        )}

        <div className="exam-layout">
          {/* Left Column: Exam Questions */}
          <div className="card">
            <h1 style={{ fontSize: '1.4rem', color: '#0f172a', marginBottom: 4 }}>{exam.title}</h1>
            <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: 20 }}>{exam.description}</p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                onExamSubmitted();
              }}
            >
              {exam.questions.map((q, idx) => (
                <div key={q.id} className="question-block">
                  <div className="question-prompt">
                    {idx + 1}. {q.prompt}
                  </div>

                  {q.type === 'mcq' && q.options && (
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      {q.options.map((opt, optIdx) => {
                        const isSelected = answers[q.id] === opt;
                        return (
                          <label
                            key={optIdx}
                            className={`option-label ${isSelected ? 'selected' : ''}`}
                          >
                            <input
                              type="radio"
                              name={q.id}
                              value={opt}
                              checked={isSelected}
                              onChange={() => handleAnswerChange(q.id, opt)}
                              disabled={isHeld}
                            />
                            <span>{opt}</span>
                          </label>
                        );
                      })}
                    </div>
                  )}

                  {q.type === 'written' && (
                    <textarea
                      className="form-textarea"
                      rows={4}
                      placeholder="Type your explanation or answer here..."
                      value={answers[q.id] || ''}
                      onChange={(e) => handleAnswerChange(q.id, e.target.value)}
                      disabled={isHeld}
                    />
                  )}
                </div>
              ))}

              <div style={{ marginTop: 24, textAlign: 'right' }}>
                <button
                  type="submit"
                  className="btn btn-primary"
                  style={{ padding: '12px 28px', fontSize: '1rem' }}
                  disabled={isHeld}
                >
                  {isHeld ? 'Exam Paused for Human Review' : 'Finish & Submit Exam'}
                </button>
              </div>
            </form>
          </div>

          {/* Right Column: Live Camera Mirror Feed & Explanation Box */}
          <div>
            {/* Live Camera Mirror Feed */}
            <div className="card" style={{ padding: 16 }}>
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#1e293b', marginBottom: 8 }}>
                Live Proctoring Feed (In-Browser Only)
              </h2>
              <div
                className="video-preview-wrapper"
                style={{ width: '100%', height: 180, margin: '0 auto 8px', borderRadius: 6 }}
              >
                <video
                  ref={videoRef}
                  className="video-element"
                  muted
                  playsInline
                  autoPlay
                />
                <div className="face-guide-overlay" style={{ width: 110, height: 140 }} />
              </div>
              <div style={{ fontSize: '0.78rem', color: '#64748b', textAlign: 'center' }}>
                🔒 Frames processed locally via WASM · Never recorded
              </div>
            </div>

            {/* Explanation Submission Box */}
            <div className="card" style={{ padding: 16 }}>
              <h2 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#1e293b', marginBottom: 6 }}>
                Submit an Explanation
              </h2>
              <p style={{ fontSize: '0.82rem', color: '#64748b', marginBottom: 12 }}>
                Notice an unexpected sound or interruption? Submit an explanation directly to your evidence ledger.
              </p>

              <form onSubmit={handleExplanationSubmit}>
                <textarea
                  className="form-textarea"
                  rows={3}
                  placeholder="e.g., Dropped my pen, family member knocked on door..."
                  value={explanationText}
                  onChange={(e) => setExplanationText(e.target.value)}
                  style={{ fontSize: '0.85rem', marginBottom: 8 }}
                />
                <button
                  type="submit"
                  className="btn btn-secondary"
                  style={{ width: '100%', fontSize: '0.85rem', padding: '6px 12px' }}
                  disabled={!explanationText.trim()}
                >
                  Save Explanation to Ledger
                </button>
              </form>

              {explanationStatus && (
                <div
                  style={{
                    marginTop: 8,
                    fontSize: '0.8rem',
                    color: explanationStatus.startsWith('✓') ? '#15803d' : '#b45309',
                    fontWeight: 500,
                  }}
                >
                  {explanationStatus}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Evidence Record Modal */}
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
