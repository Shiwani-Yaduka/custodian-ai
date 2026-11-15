# ruff: noqa: E501
"""HTML Report Generator for Custodian AI Faculty Review.

Produces a self-contained, printable, accessible HTML audit report for held sessions.
Adheres strictly to the principles in AGENTS.md:
- Transparent sensory evidence under uncertainty
- Highlights that no automated penalty was applied
- Displays Bayesian investigation logs, student statements, and human faculty determinations
"""

from __future__ import annotations

import datetime
from typing import Optional

from core.ledger.readers import FacultyTimeline


def _format_time(ts: Optional[float]) -> str:
    if not ts:
        return "N/A"
    try:
        dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(ts)


def generate_faculty_html_report(
    session_id: str,
    student_username: str,
    timeline: FacultyTimeline,
) -> str:
    """Generate a clean, printable HTML audit report for a faculty-reviewed session."""
    status_color = "#dc2626" if timeline.status.lower() == "held" else "#16a34a"
    if timeline.status.lower() in ("warned", "elevated"):
        status_color = "#d97706"

    # Decisions section
    decisions_html = ""
    if timeline.faculty_decisions:
        for d in timeline.faculty_decisions:
            verdict_badge = {
                "cleared": ("#16a34a", "CLEARED"),
                "warning_stands": ("#d97706", "WARNING STAYS"),
                "refer_onward": ("#dc2626", "REFER ONWARD"),
            }.get(d.get("verdict", ""), ("#4b5563", d.get("verdict", "").upper()))

            decisions_html += f"""
            <div style="background: #f8fafc; border-left: 4px solid {verdict_badge[0]}; padding: 12px 16px; margin-bottom: 12px; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="background: {verdict_badge[0]}; color: white; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                        {verdict_badge[1]}
                    </span>
                    <span style="color: #64748b; font-size: 12px;">{_format_time(d.get('recorded_at'))}</span>
                </div>
                <div style="font-size: 13px; color: #334155;"><strong>Faculty ID:</strong> {d.get('faculty_id')}</div>
                <div style="font-size: 13px; color: #1e293b; margin-top: 4px;"><strong>Reviewer Comment:</strong> {d.get('notes') or 'No comments provided.'}</div>
            </div>
            """
    else:
        decisions_html = """
        <div style="padding: 12px; background: #fffbeb; border: 1px solid #fef3c7; border-radius: 6px; color: #92400e; font-size: 13px;">
            ⚠️ <strong>Pending Faculty Review:</strong> No human determination recorded yet. The exam remains on hold awaiting review.
        </div>
        """

    # Student explanations
    explanations_html = ""
    if timeline.student_explanations:
        for exp in timeline.student_explanations:
            explanations_html += f"""
            <div style="background: #eff6ff; border: 1px solid #bfdbfe; padding: 10px 14px; border-radius: 6px; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #1e40af; margin-bottom: 4px;">Submitted at {_format_time(exp.get('submitted_at'))}</div>
                <div style="font-size: 13px; color: #1e3a8a; font-style: italic;">"{exp.get('explanation_text', '')}"</div>
            </div>
            """
    else:
        explanations_html = "<div style='color: #64748b; font-size: 13px;'>No explanations submitted by the student during this session.</div>"

    # Investigation cases
    cases_html = ""
    if timeline.investigation_cases:
        for c in timeline.investigation_cases:
            probes_rows = ""
            for p in c.probes:
                probes_rows += f"""
                <tr>
                    <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-family: monospace; font-size: 12px;">{p.probe_name}</td>
                    <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{p.outcome}</td>
                    <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{p.cost:.1f}</td>
                    <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 11px; color: #475569;">{p.posterior}</td>
                </tr>
                """

            res_label = c.resolution.upper() if c.resolution else "OPEN"
            cases_html += f"""
            <div style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; margin-bottom: 14px; background: #ffffff;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span style="font-weight: 600; color: #0f172a; font-size: 13px;">Case #{c.case_id} — {c.open_reason}</span>
                    <span style="font-size: 12px; font-weight: bold; padding: 2px 8px; border-radius: 4px; background: #e0e7ff; color: #3730a3;">
                        Resolution: {res_label} (Multiplier: {c.multiplier}x)
                    </span>
                </div>
                <div style="font-size: 12px; color: #64748b; margin-bottom: 8px;">
                    Opened: {_format_time(c.opened_at)} · Resolved: {_format_time(c.resolved_at)}
                </div>
                <table style="width: 100%; border-collapse: collapse; margin-top: 6px;">
                    <thead>
                        <tr style="background: #f1f5f9; text-align: left; font-size: 11px; color: #475569;">
                            <th style="padding: 6px 10px;">Probe</th>
                            <th style="padding: 6px 10px;">Outcome</th>
                            <th style="padding: 6px 10px;">Cost</th>
                            <th style="padding: 6px 10px;">Bayesian Belief Update</th>
                        </tr>
                    </thead>
                    <tbody>
                        {probes_rows if probes_rows else "<tr><td colspan='4' style='padding: 6px 10px; font-size: 12px; color: #64748b;'>No probes executed.</td></tr>"}
                    </tbody>
                </table>
            </div>
            """
    else:
        cases_html = "<div style='color: #64748b; font-size: 13px;'>No ambiguous observations required opening an investigation case.</div>"

    # Risk points & stub clip markers
    risk_rows = ""
    for rp in timeline.risk_points:
        clip_badge = f"<span style='background: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 10px;'>{rp.stub_clip_marker}</span>" if rp.stub_clip_marker else "<span style='color: #94a3b8;'>—</span>"
        gate_badge = "<span style='color: #16a34a; font-weight: bold;'>Passed</span>" if rp.gate_passed else f"<span style='color: #d97706; font-weight: bold;'>Blocked ({rp.blocked_reason or 'conditions unmet'})</span>"
        risk_rows += f"""
        <tr>
            <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{_format_time(rp.timestamp)}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-weight: bold; font-size: 12px;">{rp.score:.1f}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{rp.from_tier} → <strong>{rp.to_tier}</strong></td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{gate_badge}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #334155;">{rp.reason}</td>
            <td style="padding: 8px 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">{clip_badge}</td>
        </tr>
        """

    # Coalesced observations
    obs_rows = ""
    for obs in timeline.observations:
        obs_rows += f"""
        <tr>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{_format_time(obs.get('timestamp'))}</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-weight: 500; font-size: 12px;">{obs.get('signal', '').replace('_', ' ').title()}</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{obs.get('duration', 0.0):.1f} s</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px;">{int(obs.get('confidence', 0.0) * 100)}%</td>
            <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">{obs.get('plain_summary', '')}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Custodian AI Audit Report — {session_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #0f172a;
            line-height: 1.5;
            background: #f8fafc;
            margin: 0;
            padding: 24px;
        }}
        .report-card {{
            max-width: 960px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            padding: 32px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 20px;
            margin-bottom: 24px;
        }}
        .title {{
            font-size: 22px;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 6px 0;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            text-transform: uppercase;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-box {{
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: 12px 16px;
        }}
        .stat-label {{
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            margin-bottom: 4px;
        }}
        .stat-value {{
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 700;
            color: #1e293b;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            margin: 28px 0 12px 0;
            padding-bottom: 6px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .callout-fairness {{
            background: #f0fdf4;
            border-left: 4px solid #16a34a;
            padding: 12px 16px;
            border-radius: 4px;
            font-size: 13px;
            color: #166534;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
        }}
        th {{
            background: #f1f5f9;
            text-align: left;
            padding: 8px 10px;
            font-size: 12px;
            color: #475569;
            font-weight: 600;
        }}
        @media print {{
            body {{
                background: #ffffff;
                padding: 0;
            }}
            .report-card {{
                box-shadow: none;
                padding: 0;
                max-width: 100%;
            }}
            .no-print {{
                display: none !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="report-card">
        <div class="no-print" style="margin-bottom: 20px; text-align: right;">
            <button onclick="window.print()" style="background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">
                🖨️ Print / Save as PDF
            </button>
        </div>

        <div class="header">
            <div>
                <h1 class="title">Custodian AI — Proctoring Integrity Audit Report</h1>
                <div style="font-size: 13px; color: #64748b;">
                    Session: <strong>{session_id}</strong> · Candidate: <strong>{student_username}</strong> · Started: {_format_time(timeline.start_time)}
                </div>
            </div>
            <div>
                <span class="badge" style="background: {status_color}; color: white;">
                    {timeline.status.upper()}
                </span>
            </div>
        </div>

        <div class="callout-fairness">
            🛡️ <strong>Fairness & Human Sovereignty Guarantee:</strong>
            Custodian AI treats observations as evidence under uncertainty, never as automated verdicts.
            No automated failing, marks deduction, or punitive action can occur. All disciplinary outcomes
            are reserved strictly for faculty decision-making.
        </div>

        <div class="stats-grid">
            <div class="stat-box">
                <div class="stat-label">Peak Risk Score</div>
                <div class="stat-value">{timeline.peak_risk_score:.1f} / 100</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Warnings Shown</div>
                <div class="stat-value">{len(timeline.warnings_issued)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Investigation Cases</div>
                <div class="stat-value">{len(timeline.investigation_cases)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Student Explanations</div>
                <div class="stat-value">{len(timeline.student_explanations)}</div>
            </div>
        </div>

        <div class="section-title">Official Human Faculty Determination</div>
        {decisions_html}

        <div class="section-title">Student Statement / Explanations</div>
        {explanations_html}

        <div class="section-title">Investigation Agent Audit & Bayesian Probes</div>
        {cases_html}

        <div class="section-title">Risk Progression, Gating & Evidence Stub Markers</div>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Risk</th>
                    <th>Tier Transition</th>
                    <th>Gating Check</th>
                    <th>Reason</th>
                    <th style="text-align: center;">Clip Stub</th>
                </tr>
            </thead>
            <tbody>
                {risk_rows if risk_rows else "<tr><td colspan='6' style='padding: 8px 10px; font-size: 12px; color: #64748b;'>No tier changes recorded.</td></tr>"}
            </tbody>
        </table>

        <div class="section-title">Sensory Observation Ledger (Coalesced Episodes)</div>
        <table>
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Signal</th>
                    <th>Duration</th>
                    <th>Confidence</th>
                    <th>Observed Details</th>
                </tr>
            </thead>
            <tbody>
                {obs_rows if obs_rows else "<tr><td colspan='5' style='padding: 8px 10px; font-size: 12px; color: #64748b;'>No sensory anomalies recorded.</td></tr>"}
            </tbody>
        </table>

        <div style="margin-top: 36px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center;">
            Generated by Custodian AI Adaptive Proctoring System · Designed with Student Fairness & Privacy Sovereignty
        </div>
    </div>
</body>
</html>
"""
    return html
