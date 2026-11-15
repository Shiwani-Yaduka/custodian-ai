# ruff: noqa: E402, E501
"""Command-line interface for the Custodian AI Policy Simulator.

Usage Examples:
    python simulator/cli.py --grace-gaze 2.0
    python simulator/cli.py --grace-gaze 0.5 --cap-camera 44.0
    python simulator/cli.py --corroboration-lambda 0.35
    python simulator/cli.py --param signals.face_absent.b_s=25.0
    python simulator/cli.py --show-all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.policy import load_policy
from simulator.engine import build_modified_policy, run_simulation


def format_table_row(cols: list[str], widths: list[int]) -> str:
    """Format single row with pipe separators."""
    padded = [c.ljust(w)[:w] for c, w in zip(cols, widths, strict=False)]
    return "| " + " | ".join(padded) + " |"


def print_simulation_report(report: Any, show_all: bool = False) -> None:
    """Print beautifully styled ASCII comparison table."""
    print("\n" + "=" * 90)
    print(" CUSTODIAN AI — POLICY WHAT-IF SIMULATOR REPORT")
    print("=" * 90)

    print("\nPARAMETER OVERRIDES TESTED:")
    if not report.parameter_overrides:
        print("  (None — replaying base policy against itself)")
    else:
        for k, v in report.parameter_overrides.items():
            print(f"  • {k}: {v}")

    print("\n" + "-" * 90)
    print(" HIGH-LEVEL METRICS COMPARISON")
    print("-" * 90)

    base_ff_pct = f"{report.base_false_flag_rate * 100:.1f}% ({report.base_false_flags})"
    cand_ff_pct = f"{report.candidate_false_flag_rate * 100:.1f}% ({report.candidate_false_flags})"
    ff_diff = (report.candidate_false_flag_rate - report.base_false_flag_rate) * 100

    base_m_pct = f"{report.base_miss_rate * 100:.1f}% ({report.base_misses})"
    cand_m_pct = f"{report.candidate_miss_rate * 100:.1f}% ({report.candidate_misses})"
    m_diff = (report.candidate_miss_rate - report.base_miss_rate) * 100

    print(f"  Total Scenarios Evaluated : {report.total_scenarios}")
    print(f"  False Flag Rate (Innocent): {base_ff_pct} -> {cand_ff_pct} (Diff: {ff_diff:+.1f}%)")
    print(f"  Miss Rate (Violations)    : {base_m_pct} -> {cand_m_pct} (Diff: {m_diff:+.1f}%)")
    print(f"  Outcome Changes           : {report.regressions_count} regressions, {report.improvements_count} improvements, {report.unchanged_count} unchanged")

    verdict_badge = {
        "SAFE": "[ SAFE / NEUTRAL POLICY CHANGE ]",
        "REGRESSION": "[ ❌ FAIRNESS REGRESSION DETECTED ]",
        "IMPROVEMENT": "[ 🟢 POLICY IMPROVEMENT OBSERVED ]",
    }.get(report.verdict, report.verdict)

    print(f"\n  Final Simulation Verdict  : {verdict_badge}")

    # Per-scenario diff table
    diffs_to_show = report.diffs if show_all else [d for d in report.diffs if d.status_change != "UNCHANGED" or abs(d.score_delta) > 0.1]

    if not diffs_to_show:
        print("\n  No score or tier shifts occurred across benchmark scenarios.")
    else:
        print("\n" + "-" * 90)
        title_str = "ALL SCENARIO COMPARISONS" if show_all else "CHANGED SCENARIO COMPARISONS"
        print(f" {title_str} ({len(diffs_to_show)} items)")
        print("-" * 90)

        widths = [26, 13, 14, 8, 18, 12]
        headers = ["Scenario ID", "Label", "Score (B->C)", "Delta", "Tier (B->C)", "Status"]

        print(format_table_row(headers, widths))
        print("|" + "|".join(["-" * (w + 2) for w in widths]) + "|")

        for d in diffs_to_show:
            score_str = f"{d.base_score:.1f} -> {d.candidate_score:.1f}"
            delta_str = f"{d.score_delta:+.1f}"
            tier_str = f"{d.base_tier[:4]} -> {d.candidate_tier[:4]}"
            status_tag = {
                "REGRESSION": "REGRESSION",
                "IMPROVEMENT": "IMPROVED",
                "UNCHANGED": "UNCHANGED",
            }.get(d.status_change, d.status_change)

            row = [
                d.scenario_id,
                d.label,
                score_str,
                delta_str,
                tier_str,
                status_tag,
            ]
            print(format_table_row(row, widths))

    print("=" * 90 + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Custodian AI Policy What-If Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--scenarios-file",
        type=Path,
        default=PROJECT_ROOT / "fairness" / "scenarios.yaml",
        help="Path to scenarios YAML file (default: fairness/scenarios.yaml)",
    )
    parser.add_argument(
        "--policy-file",
        type=Path,
        default=None,
        help="Custom candidate RiskPolicy YAML file",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default=None,
        help="Target single scenario ID to simulate",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Show all scenarios in table, including unchanged ones",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of ASCII table",
    )

    # Shorthand parameter overrides
    parser.add_argument("--grace-gaze", type=float, help="Grace duration for gaze_off_screen (s)")
    parser.add_argument("--grace-face", type=float, help="Grace duration for face_absent (s)")
    parser.add_argument("--grace-head", type=float, help="Grace duration for head_turn (s)")
    parser.add_argument("--grace-speech", type=float, help="Grace duration for speech_detected (s)")
    parser.add_argument("--cap-camera", type=float, help="Channel cap for camera (K_camera)")
    parser.add_argument("--cap-mic", type=float, help="Channel cap for microphone (K_mic)")
    parser.add_argument("--cap-window", type=float, help="Channel cap for exam_window")
    parser.add_argument("--cap-device", type=float, help="Channel cap for device")
    parser.add_argument("--corroboration-lambda", type=float, help="Corroboration multiplier lambda")
    parser.add_argument("--half-life", type=float, help="Accumulator half-life in seconds (H)")
    parser.add_argument("--hysteresis", type=float, help="Hysteresis seconds")

    # Generic overrides
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        help="Arbitrary parameter override in key=val format (e.g. signals.gaze_off_screen.b_s=20.0)",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overrides: Dict[str, Any] = {}

    if args.grace_gaze is not None:
        overrides["grace_gaze"] = args.grace_gaze
    if args.grace_face is not None:
        overrides["grace_face"] = args.grace_face
    if args.grace_head is not None:
        overrides["grace_head"] = args.grace_head
    if args.grace_speech is not None:
        overrides["grace_speech"] = args.grace_speech
    if args.cap_camera is not None:
        overrides["cap_camera"] = args.cap_camera
    if args.cap_mic is not None:
        overrides["cap_mic"] = args.cap_mic
    if args.cap_window is not None:
        overrides["cap_window"] = args.cap_window
    if args.cap_device is not None:
        overrides["cap_device"] = args.cap_device
    if args.corroboration_lambda is not None:
        overrides["corroboration_lambda"] = args.corroboration_lambda
    if args.half_life is not None:
        overrides["half_life"] = args.half_life
    if args.hysteresis is not None:
        overrides["hysteresis"] = args.hysteresis

    for p in args.param:
        if "=" not in p:
            print(f"Error: Invalid param format '{p}'. Expected key=value", file=sys.stderr)
            return 2
        k, v = p.split("=", 1)
        # Attempt float or bool parsing
        try:
            val: Any = float(v)
        except ValueError:
            if v.lower() in ("true", "false"):
                val = v.lower() == "true"
            else:
                val = v
        overrides[k.strip()] = val

    # Load base policy
    base_policy = load_policy()

    # Load or build candidate policy
    try:
        if args.policy_file:
            candidate_policy = load_policy(args.policy_file)
        else:
            candidate_policy = build_modified_policy(base_policy, overrides)
    except Exception as e:
        print(f"\n[Policy Validation Error]: {e}", file=sys.stderr)
        return 2

    # Run simulation
    report = run_simulation(
        scenarios_path=args.scenarios_file,
        modified_policy=candidate_policy,
        base_policy=base_policy,
        target_scenario=args.scenario,
    )
    report.parameter_overrides = overrides

    if args.json:
        print(json.dumps(report.model_dump(), indent=2))
    else:
        print_simulation_report(report, show_all=args.show_all)

    # Return exit code: 0 if safe or improvement, 1 if regression
    return 1 if report.verdict == "REGRESSION" else 0


if __name__ == "__main__":
    sys.exit(main())
