#!/usr/bin/env python3
"""Custodian AI — Developer Task Runner & CLI.

Cross-platform management script for Windows, Linux, and macOS without requiring
system make or Docker.

Usage:
    python scripts/dev.py setup
    python scripts/dev.py test
    python scripts/dev.py lint
    python scripts/dev.py fairness
    python scripts/dev.py seed
    python scripts/dev.py run
    python scripts/dev.py stop
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PID_FILE = ROOT / ".services.pids"

# Detect virtual environment python
if os.name == "nt":
    VENV_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
    VENV_RUFF = ROOT / ".venv" / "Scripts" / "ruff.exe"
    VENV_PYTEST = ROOT / ".venv" / "Scripts" / "pytest.exe"
else:
    VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
    VENV_RUFF = ROOT / ".venv" / "bin" / "ruff"
    VENV_PYTEST = ROOT / ".venv" / "bin" / "pytest"


def get_python() -> str:
    """Return the venv python if available, else current interpreter."""
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable


def run_command(cmd: str, cwd: str | None = None) -> int:
    """Execute command in project root or specified directory."""
    print(f"\n[dev.py] -> {cmd}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    res = subprocess.run(cmd, shell=True, cwd=cwd or str(ROOT), env=env)
    return res.returncode


def cmd_setup():
    """Set up virtual environment and install dependencies."""
    print("=== [setup] Setting up Custodian AI environment ===")
    if not (ROOT / ".venv").exists():
        print("Creating virtual environment at .venv...")
        subprocess.check_call([sys.executable, "-m", "venv", str(ROOT / ".venv")])
    py = get_python()
    pip_cmd = f'"{py}" -m pip install -r requirements.txt'
    code = run_command(pip_cmd)
    if code == 0:
        print("\nSetup completed successfully!")
    return code


def cmd_test():
    """Run backend pytest suite and frontend vitest suite."""
    print("=== [test] Running backend test suite ===")
    py = get_python()
    test_cmd = f'"{py}" -m pytest'
    code = run_command(test_cmd)
    if code != 0:
        return code

    web_pkg = ROOT / "web" / "package.json"
    if web_pkg.exists():
        print("\n=== [test] Running frontend vitest suite ===")
        v_name = "vitest.cmd" if os.name == "nt" else "vitest"
        vitest_bin = ROOT / "web" / "node_modules" / ".bin" / v_name
        if vitest_bin.exists():
            return run_command(f'"{vitest_bin}" run', cwd=str(ROOT / "web"))
    return code


def cmd_lint():
    """Run ruff linter."""
    print("=== [lint] Running linter ===")
    py = get_python()
    lint_cmd = f'"{py}" -m ruff check .'
    return run_command(lint_cmd)


def cmd_fairness():
    """Run fairness evaluation suite."""
    print("=== [fairness] Running fairness evaluation suite ===")
    py = get_python()
    fairness_cmd = f'"{py}" -m pytest fairness/'
    return run_command(fairness_cmd)


def cmd_seed():
    """Seed demo accounts and Demo Exam."""
    print("=== [seed] Seeding demo database ===")
    py = get_python()
    return run_command(f'"{py}" scripts/seed.py')


def check_health(port: int) -> bool:
    """Check if service or web frontend on port is responding."""
    url = f"http://127.0.0.1:{port}/" if port == 5173 else f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=1.0) as resp:
            return resp.status in (200, 304)
    except Exception:
        return False


def kill_pid(pid: int) -> None:
    """Terminate process cleanly cross-platform."""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass


def cmd_run():
    """Start all 5 services with plain uvicorn and wait for health checks."""
    print("=== [run] Starting Custodian AI microservices (Laptop-Light Mode) ===")

    # Stop any previously running services first
    cmd_stop(silent=True)

    py = get_python()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONUNBUFFERED"] = "1"

    services = [
        ("capture-detect", "services.capture_detect.main:app", 8001),
        ("risk-engine", "services.risk_engine.main:app", 8002),
        ("investigator", "services.investigator.main:app", 8003),
        ("warn-escalate", "services.warn_escalate.main:app", 8004),
        ("review-report", "services.review_report.main:app", 8005),
    ]

    pids = {}
    processes = []

    creationflags = 0
    start_new_session = False
    if os.name == "nt":
        detached = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | detached
    else:
        start_new_session = True

    print("\nSpawning services...")
    for name, module, port in services:
        cmd = [
            py,
            "-m",
            "uvicorn",
            module,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ]
        proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )
        pids[name] = proc.pid
        processes.append((name, port, proc))
        print(f"  • {name:<15} [PID {proc.pid}] on port {port}")

    # Launch Vite Web Frontend if present
    vite_bin = ROOT / "web" / "node_modules" / ".bin" / ("vite.cmd" if os.name == "nt" else "vite")
    if vite_bin.exists():
        vite_cmd = f'"{vite_bin}" --port 5173 --host 127.0.0.1'
        vite_proc = subprocess.Popen(
            vite_cmd,
            shell=True,
            cwd=str(ROOT / "web"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            start_new_session=start_new_session,
        )
        pids["web-frontend"] = vite_proc.pid
        processes.append(("web-frontend", 5173, vite_proc))
        print(f"  • {'web-frontend':<15} [PID {vite_proc.pid}] on port 5173")

    # Save PIDs
    with open(PID_FILE, "w") as f:
        json.dump(pids, f, indent=2)

    # Wait for health/readiness on all ports
    print("\nWaiting for health/readiness checks...")
    start_time = time.time()
    max_wait = 15.0  # seconds

    all_healthy = False
    while time.time() - start_time < max_wait:
        healthy_count = sum(1 for _, port, _ in processes if check_health(port))
        if healthy_count == len(processes):
            all_healthy = True
            break
        time.sleep(0.5)

    if all_healthy:
        print("\nAll services and web frontend are healthy and running:")
        for name, port, _ in processes:
            health_path = "/" if port == 5173 else "/health"
            print(f"  ✓ {name:<15} -> http://127.0.0.1:{port} (health: http://127.0.0.1:{port}{health_path})")
        print("\nReady! Open http://127.0.0.1:5173 in your browser.")
        print("To stop all services cleanly, run: python scripts/dev.py stop (or press Ctrl+C)", flush=True)
        sys.stdout.flush()

        if "--detach" in sys.argv:
            return 0

        try:
            while True:
                time.sleep(1.0)
        except (KeyboardInterrupt, SystemExit):
            cmd_stop()
        return 0
    else:
        print("\nWarning: Some services did not report healthy within 15 seconds.")
        for name, port, _ in processes:
            status = "HEALTHY" if check_health(port) else "FAILED / PENDING"
            print(f"  - {name:<15} (port {port}): {status}")
        return 1


def cmd_stop(silent: bool = False):
    """Stop all running dev services."""
    if not silent:
        print("=== [stop] Stopping development services ===")

    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pids = json.load(f)
            for name, pid in pids.items():
                if not silent:
                    print(f"Stopping {name} [PID {pid}]...")
                kill_pid(pid)
            PID_FILE.unlink(missing_ok=True)
            if not silent:
                print("All services stopped.")
        except Exception as e:
            if not silent:
                print(f"Error stopping services: {e}")
    else:
        if not silent:
            print("No active service PID file found.")
    return 0


def print_help():
    print(__doc__)


def main():
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    cmd = sys.argv[1].lower()
    commands = {
        "setup": cmd_setup,
        "test": cmd_test,
        "lint": cmd_lint,
        "fairness": cmd_fairness,
        "seed": cmd_seed,
        "run": cmd_run,
        "stop": cmd_stop,
        "help": print_help,
    }

    if cmd in commands:
        exit_code = commands[cmd]()
        sys.exit(exit_code or 0)
    else:
        print(f"Unknown command: {cmd}")
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
