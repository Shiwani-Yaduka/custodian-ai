"""Baseline test for fairness suite."""


def test_fairness_baseline_ready():
    """Verify fairness package is ready to receive evaluation scenarios."""
    import fairness

    assert fairness is not None
