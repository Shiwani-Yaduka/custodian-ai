"""Central Configuration Module for Custodian AI.

Loads and validates all application settings from environment variables or .env file
using Pydantic Settings.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable bindings and safe defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    app_env: Literal["development", "testing", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    debug: bool = Field(default=True, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Security & Auth
    jwt_secret: str = Field(
        default="dev-insecure-custodian-ai-secret-key-change-in-production",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=120, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # Demo Credentials
    demo_student1_username: str = Field(default="student1", alias="DEMO_STUDENT1_USERNAME")
    demo_student1_password: str = Field(default="student1pass", alias="DEMO_STUDENT1_PASSWORD")
    demo_student2_username: str = Field(default="student2", alias="DEMO_STUDENT2_USERNAME")
    demo_student2_password: str = Field(default="student2pass", alias="DEMO_STUDENT2_PASSWORD")
    demo_faculty1_username: str = Field(default="faculty1", alias="DEMO_FACULTY1_USERNAME")
    demo_faculty1_password: str = Field(default="faculty1pass", alias="DEMO_FACULTY1_PASSWORD")

    # Database
    database_url: str = Field(
        default="sqlite:///./custodian.db",
        alias="DATABASE_URL",
    )

    # Service Ports (Phase A uvicorn processes)
    capture_detect_port: int = Field(default=8001, alias="CAPTURE_DETECT_PORT")
    risk_engine_port: int = Field(default=8002, alias="RISK_ENGINE_PORT")
    investigator_port: int = Field(default=8003, alias="INVESTIGATOR_PORT")
    warn_escalate_port: int = Field(default=8004, alias="WARN_ESCALATE_PORT")
    review_report_port: int = Field(default=8005, alias="REVIEW_REPORT_PORT")

    # Risk Engine Model Parameters (AGENTS.md Section 5)
    risk_half_life_seconds: float = Field(default=240.0, alias="RISK_HALF_LIFE_SECONDS")
    channel_accumulator_cap: float = Field(default=40.0, alias="CHANNEL_ACCUMULATOR_CAP")
    corroboration_lambda: float = Field(default=0.20, alias="CORROBORATION_LAMBDA")
    tier_hysteresis_seconds: float = Field(default=6.0, alias="TIER_HYSTERESIS_SECONDS")
    mass_flag_window_seconds: float = Field(default=60.0, alias="MASS_FLAG_WINDOW_SECONDS")
    mass_flag_session_ratio: float = Field(default=0.30, alias="MASS_FLAG_SESSION_RATIO")


@lru_cache()
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()
