import React, { useState } from 'react';
import { api } from '../api';
import { UserSession } from '../types';

interface LoginScreenProps {
  onLoginSuccess: (session: UserSession, isPractice: boolean) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('student1');
  const [password, setPassword] = useState('student1pass');
  const [isPractice, setIsPractice] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    if (isPractice) {
      // In practice mode, synthesize a mock session immediately without requiring backend
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

  const fillAccount = (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setError(null);
  };

  return (
    <div style={{ maxWidth: 480, margin: '40px auto', width: '100%' }}>
      <div className="card">
        <h1 style={{ fontSize: '1.5rem', marginBottom: 8, color: '#0f172a' }}>Sign in to Exam Portal</h1>
        <p style={{ color: '#64748b', fontSize: '0.95rem', marginBottom: 24 }}>
          Custodian AI — Adaptive, Privacy-First Exam Proctoring
        </p>

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
          <div className="form-group">
            <label className="form-label" htmlFor="username">
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
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
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
            />
          </div>

          <div style={{ margin: '16px 0', padding: 12, background: '#f8fafc', borderRadius: 6 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer', fontSize: '0.9rem' }}>
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

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: '100%', marginTop: 8 }}
            disabled={loading}
          >
            {loading ? 'Signing in...' : isPractice ? 'Start Practice Session' : 'Sign In & Continue'}
          </button>
        </form>

        <div style={{ marginTop: 28, paddingTop: 20, borderTop: '1px solid #e2e8f0' }}>
          <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: 10 }}>
            Demo Accounts (click to pre-fill):
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: '0.85rem', padding: '6px 12px' }}
              onClick={() => fillAccount('student1', 'student1pass')}
            >
              student1 (pass: student1pass)
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ fontSize: '0.85rem', padding: '6px 12px' }}
              onClick={() => fillAccount('student2', 'student2pass')}
            >
              student2 (pass: student2pass)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
