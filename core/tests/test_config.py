"""Test configuration loading from environment and defaults."""

from shared.config import get_settings


def test_settings_load_defaults():
    settings = get_settings()
    assert settings.jwt_secret is not None
    assert settings.channel_accumulator_cap == 40.0
    assert settings.risk_half_life_seconds == 240.0
    assert settings.demo_student1_username == "student1"
    assert settings.demo_faculty1_username == "faculty1"
