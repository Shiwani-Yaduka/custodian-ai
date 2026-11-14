#!/usr/bin/env python3
"""Custodian AI — Developer Task Runner & CLI.

Cross-platform management script for Windows, Linux, and macOS without requiring
system make or Docker.

Usage:
    python scripts/dev.py setup
    python scripts/dev.py test
    python scripts/dev.py lint
    python scripts/dev.py fairness
    python scripts/dev.py run
    python scripts/dev.py stop
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

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


def get_pytest() -> str:
    """Return venv pytest executable or fallback."""
    if VENV_PYTEST.exists():
        return str(VENV_PYTEST)
    return f"{get_python()} -m pytest"


def get_ruff() -> str:
    """Return venv ruff executable or fallback."""
    if VENV_RUFF.exists():
        return str(VENV_RUFF)
    return f"{get_python()} -m ruff"


def run_command(cmd: str) -> int:
    """Execute command in project root."""
    print(f"\n[dev.py] -> {cmd}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    res = subprocess.run(cmd, shell=True, cwd=str(ROOT), env=env)
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
    """Run pytest suite."""
    print("=== [test] Running test suite ===")
    py = get_python()
    test_cmd = f'"{py}" -m pytest'
    return run_command(test_cmd)


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


def cmd_run():
    """Start services in laptop-light mode."""
    print("=== [run] Starting services (Phase A) ===")
    print("Note: Service endpoints will be available as each phase builds out.")
    print("Currently on Step A0: Core foundation ready.")
    return 0


def cmd_stop():
    """Stop running dev services."""
    print("=== [stop] Stopping development services ===")
    print("All processes stopped.")
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
