import React, { useState } from 'react';
import { api } from '../api';
import { UserSession } from '../types';

interface LoginScreenProps {
  onLoginSuccess: (session: UserSession, isPractice: boolean) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [selectedRole, setSelectedRole] = useState<'student' | 'faculty'>('student');
  const [username, setUsername] = useState('student1');
  const [password, setPassword] = useState('student1pass');
  const [isPractice, setIsPractice] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectRole = (role: 'student' | 'faculty') => {
    setSelectedRole(role);
    setError(null);
    if (role === 'faculty') {
      setUsername('faculty1');
      setPassword('faculty1pass');
      setIsPractice(false);
    } else {
      setUsername('student1');
      setPassword('student1pass');
    }
  };

  const fillAccount = (user: string, pass: string, role: 'student' | 'faculty') => {
    setUsername(user);
    setPassword(pass);
    setSelectedRole(role);
    if (role === 'faculty') {
      setIsPractice(false);
    }
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (isPractice && selectedRole === 'student') {
      // In practice mode, synthesize a mock session locally without requiring backend
      onLoginSuccess(
        {
          token: 'practice-mock-token',
          user_id: 1,
          username: username || 'practice_student',
          role: 'student',
        },
        true
      );
      setLoading(false);
      return;
    }

    try {
      const session = await api.login(username, password);
      onLoginSuccess(session, false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 520, margin: '40px auto', width: '100%', padding: '0 16px' }}>
      <div className="card" style={{ padding: 28, borderRadius: 12, boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
        <h1 style={{ fontSize: '1.5rem', marginBottom: 4, color: '#0f172a', fontWeight: 700 }}>
          Custodian AI Portal
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.9rem', marginBottom: 20 }}>
          Adaptive, Privacy-First Exam Proctoring & Faculty Adjudication
        </p>

        {/* Role Selector Tabs */}
        <div
          style={{
            display: 'flex',
            gap: 6,
            marginBottom: 20,
            background: '#f1f5f9',
            padding: 4,
            borderRadius: 8,
          }}
        >
          <button
            type="button"
            onClick={() => selectRole('student')}
            style={{
              flex: 1,
              padding: '10px 14px',
              border: 'none',
              borderRadius: 6,
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              background: selectedRole === 'student' ? '#ffffff' : 'transparent',
              color: selectedRole === 'student' ? '#0f172a' : '#64748b',
              boxShadow: selectedRole === 'student' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.15s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            🎓 Student Exam
          </button>
          <button
            type="button"
            onClick={() => selectRole('faculty')}
            style={{
              flex: 1,
              padding: '10px 14px',
              border: 'none',
              borderRadius: 6,
              fontWeight: 600,
              fontSize: '0.9rem',
              cursor: 'pointer',
              background: selectedRole === 'faculty' ? '#3730a3' : 'transparent',
              color: selectedRole === 'faculty' ? '#ffffff' : '#64748b',
              boxShadow: selectedRole === 'faculty' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.15s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
            }}
          >
            👩‍🏫 Faculty Portal
          </button>
        </div>

        {selectedRole === 'faculty' && (
          <div
            style={{
              background: '#e0e7ff',
              border: '1px solid #c7d2fe',
              color: '#3730a3',
              padding: '10px 14px',
              borderRadius: 6,
              marginBottom: 16,
              fontSize: '0.85rem',
            }}
          >
            🔍 <strong>Faculty Mode:</strong> Review paused sessions on hold, inspect Bayesian investigator telemetry, and render human determinations.
          </div>
        )}

        {error && (
          <div
            role="alert"
            style={{
              background: '#fef2f2',
              color: '#b91c1c',
              border: '1px solid #fecaca',
              padding: 12,
              borderRadius: 6,
              marginBottom: 16,
              fontSize: '0.9rem',
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: 14 }}>
            <label className="form-label" htmlFor="username" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: '#334155' }}>
              Username
            </label>
            <input
              id="username"
              type="text"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
              autoComplete="username"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: '0.9rem', boxSizing: 'border-box' }}
            />
          </div>

          <div className="form-group" style={{ marginBottom: 16 }}>
            <label className="form-label" htmlFor="password" style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: 6, color: '#334155' }}>
              Password
            </label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
              autoComplete="current-password"
              style={{ width: '100%', padding: '10px 12px', borderRadius: 6, border: '1px solid #cbd5e1', fontSize: '0.9rem', boxSizing: 'border-box' }}
            />
          </div>

          {selectedRole === 'student' && (
            <div style={{ margin: '14px 0', padding: 12, background: '#f8fafc', borderRadius: 6, border: '1px solid #e2e8f0' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: '0.85rem', color: '#334155' }}>
                <input
                  type="checkbox"
                  checked={isPractice}
                  onChange={(e) => setIsPractice(e.target.checked)}
                  style={{ width: 16, height: 16 }}
                />
                <span>
                  <strong>Enable Practice Mode</strong> (Test camera & calibration locally with zero exam consequences)
                </span>
              </label>
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary"
            style={{
              width: '100%',
              marginTop: 6,
              padding: '11px',
              borderRadius: 6,
              background: selectedRole === 'faculty' ? '#3730a3' : '#2563eb',
              color: '#ffffff',
              border: 'none',
              fontWeight: 600,
              fontSize: '0.95rem',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
            disabled={loading}
          >
            {loading
              ? 'Signing in...'
              : selectedRole === 'faculty'
              ? 'Sign In to Faculty Portal →'
              : isPractice
              ? 'Start Practice Session →'
              : 'Sign In to Student Exam →'}
          </button>
        </form>

        {/* Demo Accounts List */}
        <div style={{ marginTop: 24, paddingTop: 18, borderTop: '1px solid #e2e8f0' }}>
          <p style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
            Quick Demo Accounts (Click to Fill):
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              style={{
                fontSize: '0.8rem',
                padding: '6px 12px',
                borderRadius: 6,
                background: username === 'student1' ? '#eff6ff' : '#f8fafc',
                border: `1.5px solid ${username === 'student1' ? '#2563eb' : '#cbd5e1'}`,
                color: username === 'student1' ? '#1d4ed8' : '#334155',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              onClick={() => fillAccount('student1', 'student1pass', 'student')}
            >
              🎓 student1 (Student)
            </button>
            <button
              type="button"
              style={{
                fontSize: '0.8rem',
                padding: '6px 12px',
                borderRadius: 6,
                background: username === 'student2' ? '#eff6ff' : '#f8fafc',
                border: `1.5px solid ${username === 'student2' ? '#2563eb' : '#cbd5e1'}`,
                color: username === 'student2' ? '#1d4ed8' : '#334155',
                fontWeight: 600,
                cursor: 'pointer',
              }}
              onClick={() => fillAccount('student2', 'student2pass', 'student')}
            >
              🎓 student2 (Student)
            </button>
            <button
              type="button"
              style={{
                fontSize: '0.8rem',
                padding: '6px 12px',
                borderRadius: 6,
                background: username === 'faculty1' ? '#3730a3' : '#e0e7ff',
                border: `1.5px solid ${username === 'faculty1' ? '#312e81' : '#c7d2fe'}`,
                color: username === 'faculty1' ? '#ffffff' : '#3730a3',
                fontWeight: 700,
                cursor: 'pointer',
              }}
              onClick={() => fillAccount('faculty1', 'faculty1pass', 'faculty')}
            >
              👩‍🏫 faculty1 (Faculty Reviewer)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
