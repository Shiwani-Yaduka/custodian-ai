/**
 * API client for Custodian AI backend microservices.
 */
import { CONFIG } from './config';
import { Exam, StudentTimelineItem, UserSession } from './types';

export interface PendingProbe {
  probe_name: string;
  type: string;
  message?: string;
  session_id: string;
}

export interface RiskStateResponse {
  session_id: string;
  current_score: number;
  candidate_tier: string;
  channels: Record<string, { accumulator: number; is_discounted: boolean }>;
  contributing_channels: string[];
}

export const api = {
  async login(username: string, password: string): Promise<UserSession> {
    const res = await fetch(`${CONFIG.REVIEW_REPORT_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    return {
      token: data.access_token,
      user_id: data.user_id,
      username: data.username,
      role: data.role,
    };
  },

  async getExams(): Promise<Exam[]> {
    const res = await fetch(`${CONFIG.REVIEW_REPORT_URL}/exams`);
    if (!res.ok) throw new Error('Failed to load exams');
    return res.json();
  },

  async startSession(token: string, examId: number, sessionId?: string): Promise<string> {
    const res = await fetch(`${CONFIG.REVIEW_REPORT_URL}/sessions/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        exam_id: examId,
        session_id: sessionId,
      }),
    });
    if (!res.ok) throw new Error('Failed to start session');
    const data = await res.json();
    return data.session_id;
  },

  async submitExplanation(sessionId: string, explanation: string): Promise<void> {
    const res = await fetch(`${CONFIG.REVIEW_REPORT_URL}/student/explain`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        explanation_text: explanation,
      }),
    });
    if (!res.ok) throw new Error('Failed to submit explanation');
  },

  async getStudentRecord(sessionId: string): Promise<{
    session_id: string;
    student_name: string;
    timeline: StudentTimelineItem[];
    plain_text_summary: string;
  }> {
    const res = await fetch(`${CONFIG.REVIEW_REPORT_URL}/student/record/${sessionId}`);
    if (!res.ok) throw new Error('Failed to load student evidence record');
    return res.json();
  },

  async pollPendingProbes(sessionId: string): Promise<PendingProbe | null> {
    try {
      const res = await fetch(`${CONFIG.INVESTIGATOR_URL}/probes/pending/${sessionId}`);
      if (!res.ok) return null;
      const data = await res.json();
      return data.pending_probe || null;
    } catch {
      return null;
    }
  },

  async respondToProbe(sessionId: string, probeName: string, outcome: string): Promise<void> {
    await fetch(`${CONFIG.INVESTIGATOR_URL}/probes/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        probe_name: probeName,
        outcome,
      }),
    }).catch((err) => console.warn('[API] Probe response error:', err));
  },

  async getRiskState(sessionId: string): Promise<RiskStateResponse | null> {
    try {
      const res = await fetch(`${CONFIG.RISK_ENGINE_URL}/state/${sessionId}`);
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  },
};
