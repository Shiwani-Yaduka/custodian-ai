#!/usr/bin/env python3
"""Custodian AI — Interactive Investigator Playground.

Step-by-step interactive CLI to inspect case opening, Expected Information Gain,
optimal probe selection, Bayesian updates, and resolution decisions.

Usage:
    python scripts/investigator_playground.py
    python scripts/investigator_playground.py --demo
"""

import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.investigator import (  # noqa: E402
    InvestigatorAgent,
    ScriptedProbeRunner,
    SimulatedProbeRunner,
    calculate_expected_information_gain,
    load_investigator_policy,
)
from core.models import Observation  # noqa: E402


def render_belief(belief: dict) -> str:
    """Format hypothesis probabilities as a visual percentage bar."""
    lines = []
    for h, p in sorted(belief.items()):
        bar = "#" * int(p * 20) + "-" * (20 - int(p * 20))
        lines.append(f"  • {h:12} : [{bar}] {p * 100:5.1f}%")
    return "\n".join(lines)


def run_demo():
    """Run an illustrative automated investigation scenario."""
    print("=" * 68)
    print(" CUSTODIAN AI — BAYESIAN INVESTIGATION AGENT DEMO")
    print("=" * 68)

    policy = load_investigator_policy()
    # Script outcomes to simulate a candidate with a network telemetry spike
    runner = ScriptedProbeRunner({
        "device_telemetry_check": "hardware_normal",
        "network_heartbeat_check": "packet_loss_spike",
        "secondary_detector_cross_check": "disagrees_normal",
    })
    agent = InvestigatorAgent(policy=policy, probe_runner=runner)

    obs = Observation(
        session_id="student_investigation_demo",
        signal="network_drop",
        timestamp=100.0,
        duration=15.0,
        confidence=0.52,  # Low confidence triggers case opening
    )

    print(f"\n[EVENT] Observation Ingested: {obs.signal} on channel 'device'")
    print(f"        Duration: {obs.duration}s | Confidence: {obs.confidence:.2f}")

    case = agent.open_case(
        observation=obs,
        channel="device",
        held_raw_weight=6.0,
        reason="Low detector confidence (0.52 < 0.60)",
        now=100.0,
    )

    print(f"\n[CASE OPENED] Case ID: {case.case_id}")
    print(f"  Held Raw Weight : {case.held_raw_weight:.2f} (Held back; NOT applied to risk)")
    print(f"  Trigger Reason  : {case.open_reason}")
    print("\n[PRIOR BELIEF]:")
    print(render_belief(case.current_belief))

    step = 0
    while case.is_open:
        step += 1
        print(f"\n--- STEP {step}: PROBE EVALUATION & SELECTION ---")

        # Show candidate probes and their efficiency ratings
        print("  Evaluating Available Probes:")
        for pname, pdef in policy.probes.items():
            if any(p.probe_name == pname for p in case.probe_history):
                continue
            eig = calculate_expected_information_gain(case.current_belief, pdef)
            eff = eig / (1.0 + pdef.cost)
            print(
                f"    - {pname:30} | Cost: {pdef.cost:3.1f} | "
                f"E[IG]: {eig:5.3f} | Score: {eff:5.3f}"
            )

        best_probe = agent.select_best_probe(case)
        print(f"\n  >>> Optimal Probe Chosen: {best_probe} (Maximizes E[IG] / (1+cost))")

        record = agent.execute_next_probe(case.case_id, now=100.0 + step)
        print(f"  Outcome Observed : '{record.outcome}'")
        print("\n[UPDATED POSTERIOR BELIEF]:")
        print(render_belief(case.current_belief))

    print("\n" + "=" * 68)
    print(" CASE RESOLUTION")
    print("=" * 68)
    res = case.resolution
    print(f"  Status        : {res.status.value.upper()}")
    print(f"  Multiplier    : x{res.multiplier:.2f}")
    final_weight = case.held_raw_weight * res.multiplier
    print(
        f"  Released Risk : {case.held_raw_weight:.2f} held * x{res.multiplier:.2f} "
        f"= {final_weight:.2f}"
    )
    print(f"  Reason        : {res.reason}")
    print("=" * 68)


def interactive_cli():
    """Interactive mode allowing user to pick signals and probe outcomes."""
    policy = load_investigator_policy()
    runner = SimulatedProbeRunner(policy=policy, seed=None)
    agent = InvestigatorAgent(policy=policy, probe_runner=runner)

    print("=" * 68)
    print(" CUSTODIAN AI — Investigator Playground (Interactive)")
    print("=" * 68)
    print("Available signals:")
    signals = list(policy.signal_priors.keys())
    for idx, s in enumerate(signals, 1):
        print(f"  {idx}. {s}")

    try:
        choice = input("\nSelect a signal number [1-10] (default 1): ").strip()
        sidx = int(choice) - 1 if choice.isdigit() and 1 <= int(choice) <= len(signals) else 0
        selected_signal = signals[sidx]
    except (EOFError, KeyboardInterrupt):
        return

    obs = Observation(
        session_id="interactive_student",
        signal=selected_signal,
        timestamp=0.0,
        duration=15.0,
        confidence=0.55,
    )

    case = agent.open_case(
        obs, channel="camera", held_raw_weight=8.0, reason="Interactive test", now=0.0
    )
    print(f"\nOpened case for {selected_signal}. Prior belief:")
    print(render_belief(case.current_belief))

    while case.is_open:
        best_probe = agent.select_best_probe(case)
        pdef = policy.probes[best_probe]
        print(f"\nNext probe: {best_probe} (cost: {pdef.cost})")
        print(f"Possible outcomes: {list(pdef.outcomes.keys())}")
        outcome = input(
            f"Enter outcome (leave empty for simulated '{next(iter(pdef.outcomes))}'): "
        ).strip()
        if not outcome or outcome not in pdef.outcomes:
            outcome = next(iter(pdef.outcomes))

        agent.probe_runner = ScriptedProbeRunner({best_probe: outcome})
        agent.execute_next_probe(case.case_id, now=1.0)
        print(render_belief(case.current_belief))

    print(
        f"\nCase resolved: {case.resolution.status.value.upper()} "
        f"(Multiplier x{case.resolution.multiplier})"
    )
    print(case.resolution.reason)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo()
    else:
        run_demo()
