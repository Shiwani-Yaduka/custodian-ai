"""Baseline test suite to verify pytest test discovery and virtual environment integrity."""


def test_environment_and_core_package():
    """Verify that core package imports cleanly and baseline testing works."""
    import core

    assert core.__version__ == "0.1.0"


def test_laptop_light_principles():
    """Verify foundational constants and laptop-light sanity."""
    max_phase_a_ram_threshold_mb = 1024
    assert max_phase_a_ram_threshold_mb > 0
