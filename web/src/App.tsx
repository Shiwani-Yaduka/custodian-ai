import React, { useState } from 'react';
import { api } from './api';
import { FaceDetector } from './detection/faceLandmarker';
import { CalibrationBaseline, UserSession } from './types';
import { LoginScreen } from './screens/LoginScreen';
import { ConsentScreen } from './screens/ConsentScreen';
import { PermissionScreen } from './screens/PermissionScreen';
import { CalibrationScreen } from './screens/CalibrationScreen';
import { ExamScreen } from './screens/ExamScreen';
import { SubmittedScreen } from './screens/SubmittedScreen';

type ScreenState = 'login' | 'consent' | 'permission' | 'calibration' | 'exam' | 'submitted';

export const App: React.FC = () => {
  const [currentScreen, setCurrentScreen] = useState<ScreenState>('login');
  const [session, setSession] = useState<UserSession | null>(null);
  const [sessionId, setSessionId] = useState<string>('');
  const [isPractice, setIsPractice] = useState<boolean>(false);

  // Hardware and Detection state
  const [mediaStream, setMediaStream] = useState<MediaStream | null>(null);
  const [detector, setDetector] = useState<FaceDetector | null>(null);
  const [baseline, setBaseline] = useState<CalibrationBaseline | null>(null);

  const handleLoginSuccess = async (userSession: UserSession, practiceMode: boolean) => {
    setSession(userSession);
    setIsPractice(practiceMode);

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
    <div className="app-container">
      {currentScreen === 'login' && <LoginScreen onLoginSuccess={handleLoginSuccess} />}

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
    </div>
  );
};

export default App;
