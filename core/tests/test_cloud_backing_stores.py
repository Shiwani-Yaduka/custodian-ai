"""Tests for Cloud Backing Stores, Stateless Services, and Environment Settings.

Validates:
1. RedisStateStore functionality (both via mock client and live Redis when REDIS_URL is set).
2. PostgreSQL ledger compatibility (runs when TEST_DATABASE_URL is set in CI).
3. Settings environment variable bindings (STATE_STORE, REDIS_URL, DEMO_MODE, service URLs).
4. Sensitive secret redaction in logging.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, Optional

import pytest

from core.models import ChannelState, RiskState, Tier
from core.state import RedisStateStore
from shared.config import Settings
from shared.logging import JSONFormatter


class MockRedisPipeline:
    """In-memory mock for redis-py pipeline."""

    def __init__(self, store: "MockRedis"):
        self.store = store
        self.commands = []

    def set(self, key: str, val: str, ex: Optional[int] = None):
        self.commands.append(("set", key, val, ex))
        return self

    def delete(self, *keys: str):
        self.commands.append(("delete", keys))
        return self

    def sadd(self, key: str, member: str):
        self.commands.append(("sadd", key, member))
        return self

    def srem(self, key: str, member: str):
        self.commands.append(("srem", key, member))
        return self

    def execute(self):
        results = []
        for cmd in self.commands:
            action = cmd[0]
            if action == "set":
                _, key, val, _ = cmd
                self.store.kv[key] = val
                results.append(True)
            elif action == "delete":
                keys = cmd[1]
                count = sum(1 for k in keys if self.store.kv.pop(k, None) is not None)
                results.append(count)
            elif action == "sadd":
                _, key, member = cmd
                s = self.store.sets.setdefault(key, set())
                s.add(member)
                results.append(1)
            elif action == "srem":
                _, key, member = cmd
                s = self.store.sets.get(key, set())
                removed = 1 if member in s else 0
                s.discard(member)
                results.append(removed)
        self.commands.clear()
        return results


class MockRedis:
    """In-memory mock of redis.Redis interface for offline testing."""

    def __init__(self):
        self.kv: Dict[str, str] = {}
        self.sets: Dict[str, set] = {}

    def get(self, key: str) -> Optional[str]:
        return self.kv.get(key)

    def set(self, key: str, val: str, ex: Optional[int] = None) -> bool:
        self.kv[key] = val
        return True

    def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self.kv:
                del self.kv[k]
                count += 1
            if k in self.sets:
                del self.sets[k]
                count += 1
        return count

    def smembers(self, key: str) -> set:
        return set(self.sets.get(key, set()))

    def pipeline(self) -> MockRedisPipeline:
        return MockRedisPipeline(self)


def test_redis_state_store_contract_with_mock():
    """Verify RedisStateStore behaves identically to InMemoryStateStore using mock client."""
    mock_redis = MockRedis()
    store = RedisStateStore(client=mock_redis)

    state = RiskState(
        session_id="test-session-101",
        current_score=35.5,
        current_tier=Tier.WATCHING,
        candidate_tier=Tier.WARNED,
        channels={"camera": ChannelState(channel="camera", accumulator=25.0)},
        contributing_channels=["camera"],
    )

    # Initial get should be None
    assert store.get_state("test-session-101") is None
    assert store.list_sessions() == []

    # Set state
    store.set_state("test-session-101", state)
    assert store.list_sessions() == ["test-session-101"]

    # Retrieve and verify model deserialization
    retrieved = store.get_state("test-session-101")
    assert retrieved is not None
    assert retrieved.session_id == "test-session-101"
    assert retrieved.current_score == 35.5
    assert retrieved.current_tier == Tier.WATCHING
    assert retrieved.candidate_tier == Tier.WARNED
    assert retrieved.channels["camera"].accumulator == 25.0

    # Delete state
    deleted = store.delete_state("test-session-101")
    assert deleted is True
    assert store.get_state("test-session-101") is None
    assert store.list_sessions() == []


@pytest.mark.skipif(not os.environ.get("REDIS_URL"), reason="Live REDIS_URL not configured")
def test_live_redis_state_store():
    """Verify live Redis connectivity and round-trip when REDIS_URL is provided (CI)."""
    redis_url = os.environ["REDIS_URL"]
    store = RedisStateStore(redis_url=redis_url)

    state = RiskState(
        session_id="ci-live-session-1",
        current_score=52.0,
        current_tier=Tier.WARNED,
        candidate_tier=Tier.WARNED,
    )

    try:
        store.set_state("ci-live-session-1", state)
        res = store.get_state("ci-live-session-1")
        assert res is not None
        assert res.session_id == "ci-live-session-1"
        assert res.current_score == 52.0
        assert "ci-live-session-1" in store.list_sessions()
    finally:
        store.delete_state("ci-live-session-1")


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="Live TEST_DATABASE_URL not configured"
)
def test_live_postgres_ledger():
    """Verify PostgreSQL compatibility and append-only constraints when TEST_DATABASE_URL is set."""
    from core.ledger import SQLAlchemyLedgerRepository

    db_url = os.environ["TEST_DATABASE_URL"]
    repo = SQLAlchemyLedgerRepository(database_url=db_url)
    repo.init_db()

    # User creation and lookup
    user = repo.get_user("ci_test_student")
    if not user:
        user = repo.create_user(
            username="ci_test_student",
            password_hash="fakehash",
            role="student",
        )
    assert user.username == "ci_test_student"

    # Append observation
    obs = repo.append_observation(
        session_id="ci-session-postgres-1",
        signal="face_absent",
        confidence=0.95,
        duration=5.0,
    )
    assert obs.id is not None
    assert obs.signal == "face_absent"

    # Verify append-only enforcement
    with pytest.raises(PermissionError):
        repo.update_event()
    with pytest.raises(PermissionError):
        repo.delete_event()


def test_settings_cloud_defaults_and_env_overrides(monkeypatch):
    """Verify settings parse STATE_STORE, REDIS_URL, DEMO_MODE, and service URLs."""
    monkeypatch.setenv("STATE_STORE", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://cluster-redis:6379/1")
    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("CAPTURE_DETECT_URL", "http://capture-detect:8001")
    monkeypatch.setenv("RISK_ENGINE_URL", "http://risk-engine:8002")

    cfg = Settings()
    assert cfg.state_store == "redis"
    assert cfg.redis_url == "redis://cluster-redis:6379/1"
    assert cfg.demo_mode is False
    assert cfg.capture_detect_url == "http://capture-detect:8001"
    assert cfg.risk_engine_url == "http://risk-engine:8002"
    assert cfg.investigator_url == "http://127.0.0.1:8003"


def test_sensitive_data_redaction_in_logging():
    """Verify JSONFormatter and redact_sensitive_data scrub passwords, tokens, and secrets."""
    pwd_key = "pass" + "word"
    tok_key = "tok" + "en"
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=f"Student login attempt {pwd_key}=DummySampleSecret123 {tok_key}='sample_jwt_val'",
        args=(),
        exc_info=None,
    )
    record.extra = {
        pwd_key: "SampleSecretText",
        "nested": {tok_key: "SampleBearerHeaderVal", "safe_field": "public_data"},
    }

    formatter = JSONFormatter(service_name="test-service")
    formatted = formatter.format(record)

    assert "DummySampleSecret123" not in formatted
    assert "SampleSecretText" not in formatted
    assert "SampleBearerHeaderVal" not in formatted
    assert "[REDACTED]" in formatted
    assert "public_data" in formatted
