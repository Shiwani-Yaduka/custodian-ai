import React, { useState, useEffect } from 'react';
import { api } from './api';
import { FaceDetector } from './detection/faceLandmarker';
import { CalibrationBaseline, UserSession } from './types';
import { LoginScreen } from './screens/LoginScreen';
import { ConsentScreen } from './screens/ConsentScreen';
import { PermissionScreen } from './screens/PermissionScreen';
import { CalibrationScreen } from './screens/CalibrationScreen';
import { ExamScreen } from './screens/ExamScreen';
import { SubmittedScreen } from './screens/SubmittedScreen';
import { FacultyPortal } from './screens/FacultyPortal';
import { ScenarioPanel } from './screens/ScenarioPanel';

type ScreenState = 'login' | 'consent' | 'permission' | 'calibration' | 'exam' | 'submitted' | 'faculty';

export const App: React.FC = () => {
  const [currentScreen, setCurrentScreen] = useState<ScreenState>('login');
  const [session, setSession] = useState<UserSession | null>(null);
  const [sessionId, setSessionId] = useState<string>('');
  const [isPractice, setIsPractice] = useState<boolean>(false);
  const [isDemoOpen, setIsDemoOpen] = useState<boolean>(false);

  // Hardware and Detection state
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [detector, setDetector] = useState<FaceDetector | null>(null);
  const [baseline, setBaseline] = useState<CalibrationBaseline | null>(null);

  // Global hotkey 'd' to open demo scenario simulator
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeTag = (document.activeElement?.tagName || '').toLowerCase();
      if (activeTag === 'input' || activeTag === 'textarea') return;
      if (e.key === 'd' || e.key === 'D') {
        setIsDemoOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const handleLoginSuccess = async (userSession: UserSession, practiceMode: boolean) => {
    setSession(userSession);
    setIsPractice(practiceMode);

    if (userSession.role === 'faculty') {
      setCurrentScreen('faculty');
      return;
    }

    if (practiceMode) {
      setSessionId(`PRACTICE-${Date.now().toString().slice(-6)}`);
      setCurrentScreen('consent');
    } else {
      try {
        const newSessionId = await api.startSession(userSession.token, 1);
        setSessionId(newSessionId);
        setCurrentScreen('consent');
      } catch (err) {
        console.warn('Failed to start session on backend, falling back to local session ID:', err);
        setSessionId(`SESSION-${Date.now().toString().slice(-6)}`);
        setCurrentScreen('consent');
      }
    }
  };

  const handleConsentGiven = () => {
    setCurrentScreen('permission');
  };

  const handlePermissionGranted = (stream: MediaStream, det: FaceDetector) => {
    setMediaStream(stream);
    setDetector(det);
    setCurrentScreen('calibration');
  };

  const handleCalibrationComplete = (base: CalibrationBaseline) => {
    setBaseline(base);
    if (!isPractice && sessionId) {
      api.sendCalibration(sessionId, base).catch((err) => {
        console.warn('Failed to send calibration to backend:', err);
      });
    }
    setCurrentScreen('exam');
  };

  const handleExamSubmitted = () => {
    setCurrentScreen('submitted');
  };

  const handleSignOut = () => {
    if (mediaStream) {
      mediaStream.getTracks().forEach((track) => track.stop());
      setMediaStream(null);
    }
    if (detector) {
      detector.close();
      setDetector(null);
    }
    setSession(null);
    setSessionId('');
    setIsPractice(false);
    setBaseline(null);
    setCurrentScreen('login');
  };

  return (
    <div className="app-container" style={{ position: 'relative' }}>
      {/* Top Demo & Quick Navigation Triggers */}
      <div
        style={{
          position: 'fixed',
          top: 12,
          right: 12,
          zIndex: 900,
          display: 'flex',
          gap: 8,
          alignItems: 'center',
        }}
      >
        {session && session.role === 'student' && (
          <button
            onClick={() => {
              api.login('faculty1', 'faculty1pass').then((facSession) => {
                setSession(facSession);
                setCurrentScreen('faculty');
              });
            }}
            style={{
              background: '#3730a3',
              color: '#ffffff',
              border: '1px solid #4338ca',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
            }}
          >
            👩‍🏫 Switch to Faculty Portal
          </button>
        )}

        {session && session.role === 'faculty' && (
          <button
            onClick={() => {
              api.login('student1', 'student1pass').then((studSession) => {
                setSession(studSession);
                setCurrentScreen('exam');
              });
            }}
            style={{
              background: '#2563eb',
              color: '#ffffff',
              border: '1px solid #1d4ed8',
              padding: '6px 12px',
              borderRadius: 6,
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
            }}
          >
            🎓 Switch to Student Exam
          </button>
        )}

        <button
          onClick={() => setIsDemoOpen(true)}
          style={{
            background: '#1e293b',
            color: '#ffffff',
            border: '1px solid #475569',
            padding: '6px 12px',
            borderRadius: 6,
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 2px 4px rgba(0,0,0,0.15)',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}
          title="Press 'D' key anywhere to toggle scenario simulator"
        >
          🧪 Demo Scenarios <span style={{ background: '#334155', padding: '1px 5px', borderRadius: 3, fontSize: '0.7rem' }}>D</span>
        </button>
      </div>

      {currentScreen === 'login' && <LoginScreen onLoginSuccess={handleLoginSuccess} />}

      {currentScreen === 'faculty' && session && (
        <FacultyPortal
          session={session}
          onSignOut={handleSignOut}
          onOpenDemo={() => setIsDemoOpen(true)}
        />
      )}

      {currentScreen === 'consent' && (
        <ConsentScreen onConsentGiven={handleConsentGiven} onBack={() => setCurrentScreen('login')} />
      )}

      {currentScreen === 'permission' && (
        <PermissionScreen
          onPermissionGranted={handlePermissionGranted}
          onBack={() => setCurrentScreen('consent')}
        />
      )}

      {currentScreen === 'calibration' && mediaStream && detector && (
        <CalibrationScreen
          stream={mediaStream}
          detector={detector}
          onCalibrationComplete={handleCalibrationComplete}
          isPractice={isPractice}
        />
      )}

      {currentScreen === 'exam' && (
        <ExamScreen
          sessionId={sessionId}
          stream={mediaStream}
          detector={detector}
          baseline={
            baseline || {
              mean_gaze_offset: 0.15,
              std_gaze_offset: 0.05,
              mean_head_yaw: 0.0,
              std_head_yaw: 0.08,
              mean_head_pitch: 0.0,
              std_head_pitch: 0.08,
              mean_face_size: 0.35,
              std_face_size: 0.05,
              sample_count: 0,
            }
          }
          isPractice={isPractice}
          onExamSubmitted={handleExamSubmitted}
        />
      )}

      {currentScreen === 'submitted' && (
        <SubmittedScreen
          sessionId={sessionId}
          isPractice={isPractice}
          onSignOut={handleSignOut}
        />
      )}

      {/* Scripted Scenario Simulator Panel (DEMO MODE) */}
      <ScenarioPanel
        isOpen={isDemoOpen}
        onClose={() => setIsDemoOpen(false)}
        activeSessionId={sessionId}
      />
    </div>
  );
};

export default App;
