#!/usr/bin/env python3
"""Custodian AI — Interactive Risk Engine Playground.

Allows developers, evaluators, and students to experiment with candidate observations,
temporal decay, channel accumulators, and tier hysteresis in real time.

Usage:
    python scripts/risk_playground.py
    python scripts/risk_playground.py --demo
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.models import Observation  # noqa: E402
from core.policy import load_policy  # noqa: E402
from core.risk import RiskEngine  # noqa: E402
from core.state import InMemoryStateStore  # noqa: E402


def render_dashboard(engine: RiskEngine, session_id: str, current_time: float) -> str:
    """Format the current risk posture into a terminal dashboard."""
    state = engine.state_store.get_state(session_id)
    if not state:
        return "No active session."

    score_str = f"{state.current_score:5.1f} / 100.0"
    active_str = state.current_tier.value
    corr_str = f"{state.corroboration_multiplier:4.2f}x"
    cand_str = state.candidate_tier.value

    lines = [
        "=" * 64,
        f" SESSION: {session_id}  |  TIME: {current_time:.1f}s",
        "-" * 64,
        f" TOTAL SCORE: {score_str}   |   ACTIVE TIER:    {active_str}",
        f" CORROBORATION: {corr_str}       |   CANDIDATE TIER: {cand_str}",
        "-" * 64,
        " CHANNEL ACCUMULATORS (Cap = 40.0, Warned Threshold = 45.0):",
    ]

    for ch_name, ch_state in state.channels.items():
        bar_len = int(ch_state.accumulator / 2.0)  # max 20 chars for 40 cap
        bar = "#" * bar_len + "-" * (20 - bar_len)
        active_badge = "[ACTIVE]" if ch_state.is_contributing else "[IDLE]  "
        val_str = f"{ch_state.accumulator:5.1f} / {ch_state.cap:4.1f}"
        lines.append(f"  • {ch_name:12} : [{bar}] {val_str} {active_badge}")

    lines.append("=" * 64)
    return "\n".join(lines)


def run_demo(engine: RiskEngine, session_id: str = "demo_student"):
    """Run an automated illustrative demo session and print results."""
    print("\n>>> STARTING AUTOMATED DEMO OF CUSTODIAN AI RISK ENGINE <<<\n")
    simulated_time = 0.0

    steps = [
        ("Brief 3s glance off screen (under 4s grace window)", "gaze_off_screen", 3.0, 0.9, 0.0),
        ("Sustained head turn 15s (camera channel only)", "head_turn", 15.0, 0.9, 10.0),
        ("Repeated head turn 20s (triggers repetition multiplier)", "head_turn", 20.0, 0.95, 30.0),
        ("Wait 3 seconds (check tier hysteresis hold)", None, None, None, 3.0),
        ("Tab hidden 15s (2nd channel corroborates: exam_window)", "tab_hidden", 15.0, 1.0, 5.0),
        ("Wait 7 seconds (hysteresis triggers tier transition)", None, None, None, 7.0),
        ("Student returns to normal: Wait 240 seconds (decay)", None, None, None, 240.0),
        ("Student continues normal: Wait another 240 seconds", None, None, None, 240.0),
    ]

    for desc, sig, dur, conf, dt in steps:
        simulated_time += dt
        print(f"\n--- STEP: {desc} (t = {simulated_time:.1f}s) ---")
        if sig:
            obs = Observation(
                session_id=session_id,
                signal=sig,
                timestamp=simulated_time,
                duration=dur,
                confidence=conf,
            )
            processed, _ = engine.process_observation(obs, now=simulated_time)
            print(
                f" Ingested: {sig} | tau={dur}s | d_i={processed.duration_factor:.2f} | "
                f"r_i={processed.repetition_multiplier:.2f} | raw_w={processed.raw_weight:.2f}"
            )
        else:
            engine.evaluate_session(session_id, now=simulated_time)

        print(render_dashboard(engine, session_id, simulated_time))


def interactive_cli():
    """Run interactive REPL for manual scenario testing."""
    engine = RiskEngine(load_policy(), InMemoryStateStore())
    session_id = "interactive_session"
    simulated_time = 0.0

    init_state = engine._initialize_session_state(session_id, simulated_time)
    engine.state_store.set_state(session_id, init_state)

    print("=" * 64)
    print(" CUSTODIAN AI — Risk Engine Playground (Interactive)")
    print("=" * 64)
    print("Commands:")
    print("  obs <signal> <duration_sec> [confidence: 0-1]   (Send observation)")
    print("  tick <seconds>                                  (Advance time / decay)")
    print("  status                                          (Show dashboard)")
    print("  list                                            (List registered signals)")
    print("  demo                                            (Run automated scenario)")
    print("  quit / exit                                     (Exit playground)")
    print("=" * 64)

    while True:
        try:
            raw = input(f"\n[t={simulated_time:.1f}s] risk> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting playground.")
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd in ("exit", "quit"):
            print("Goodbye.")
            break
        elif cmd == "demo":
            run_demo(engine, session_id)
        elif cmd == "status":
            engine.evaluate_session(session_id, now=simulated_time)
            print(render_dashboard(engine, session_id, simulated_time))
        elif cmd == "list":
            print("\nRegistered Signals in Default Policy:")
            for sname, sdef in engine.policy.signals.items():
                print(
                    f"  • {sname:18} | Channel: {sdef.channel:12} | b_s={sdef.b_s:4.1f} | "
                    f"g_s={sdef.g_s:4.1f}s | f_s={sdef.f_s:4.1f}s"
                )
        elif cmd == "tick":
            if len(parts) < 2:
                print("Usage: tick <seconds>")
                continue
            try:
                dt = float(parts[1])
                simulated_time += dt
                engine.evaluate_session(session_id, now=simulated_time)
                print(f"Advanced time by {dt}s to {simulated_time:.1f}s.")
                print(render_dashboard(engine, session_id, simulated_time))
            except ValueError:
                print("Error: seconds must be a number.")
        elif cmd == "obs":
            if len(parts) < 3:
                print("Usage: obs <signal> <duration_sec> [confidence: 0-1]")
                continue
            sig = parts[1]
            try:
                dur = float(parts[2])
                conf = float(parts[3]) if len(parts) > 3 else 1.0
            except ValueError:
                print("Error: duration and confidence must be numbers.")
                continue

            obs = Observation(
                session_id=session_id,
                signal=sig,
                timestamp=simulated_time,
                duration=dur,
                confidence=conf,
            )
            processed, _ = engine.process_observation(obs, now=simulated_time)
            print(
                f"Ingested {sig}: raw_w={processed.raw_weight:.2f} "
                f"(d_i={processed.duration_factor:.2f}, r_i={processed.repetition_multiplier:.2f})"
            )
            print(render_dashboard(engine, session_id, simulated_time))
        else:
            print(f"Unknown command '{cmd}'. Try 'status', 'obs', 'tick', 'list', 'demo', 'quit'.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        engine = RiskEngine(load_policy(), InMemoryStateStore())
        run_demo(engine)
    else:
        interactive_cli()
