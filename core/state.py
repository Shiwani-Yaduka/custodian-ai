"""StateStore Interface and In-Memory Implementation for Custodian AI.

Enables pure Python session risk persistence with zero external infrastructure.
Swappable with Redis in Phase B without touching risk business logic.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, List, Optional

from core.models import RiskState


class StateStore(ABC):
    """Abstract storage interface for live exam session risk states."""

    @abstractmethod
    def get_state(self, session_id: str) -> Optional[RiskState]:
        """Retrieve the current RiskState for a session, or None if not found."""
        pass

    @abstractmethod
    def set_state(self, session_id: str, state: RiskState) -> None:
        """Persist or update the RiskState for a session."""
        pass

    @abstractmethod
    def delete_state(self, session_id: str) -> bool:
        """Remove a session's state from store. Returns True if existed."""
        pass

    @abstractmethod
    def list_sessions(self) -> List[str]:
        """Return a list of all active session IDs."""
        pass


class InMemoryStateStore(StateStore):
    """In-memory dictionary store for Phase A development, testing, and simulator runs."""

    def __init__(self) -> None:
        self._store: Dict[str, RiskState] = {}

    def get_state(self, session_id: str) -> Optional[RiskState]:
        state = self._store.get(session_id)
        if state is None:
            return None
        # Return a copy to prevent external mutation from bypassing set_state
        return deepcopy(state)

    def set_state(self, session_id: str, state: RiskState) -> None:
        self._store[session_id] = deepcopy(state)

    def delete_state(self, session_id: str) -> bool:
        if session_id in self._store:
            del self._store[session_id]
            return True
        return False

    def list_sessions(self) -> List[str]:
        return list(self._store.keys())

    def clear(self) -> None:
        """Helper to reset store between tests."""
        self._store.clear()


class RedisStateStore(StateStore):
    """Redis-backed distributed state store for multi-replica Kubernetes deployments."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        ttl_seconds: int = 86400,
        client: Optional[Any] = None,
    ) -> None:
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        if client is not None:
            self._client = client
        else:
            import redis

            self._client = redis.from_url(redis_url, decode_responses=True)

    def _state_key(self, session_id: str) -> str:
        return f"custodian:session:{session_id}:state"

    def get_state(self, session_id: str) -> Optional[RiskState]:
        key = self._state_key(session_id)
        raw = self._client.get(key)
        if not raw:
            return None
        return RiskState.model_validate_json(raw)

    def set_state(self, session_id: str, state: RiskState) -> None:
        key = self._state_key(session_id)
        payload = state.model_dump_json()
        pipe = self._client.pipeline()
        pipe.set(key, payload, ex=self.ttl_seconds)
        pipe.sadd("custodian:active_sessions", session_id)
        pipe.execute()

    def delete_state(self, session_id: str) -> bool:
        key = self._state_key(session_id)
        pipe = self._client.pipeline()
        pipe.delete(key)
        pipe.srem("custodian:active_sessions", session_id)
        results = pipe.execute()
        return bool(results[0] > 0)

    def list_sessions(self) -> List[str]:
        sessions = self._client.smembers("custodian:active_sessions")
        return list(sessions) if sessions else []

    def clear(self) -> None:
        """Reset all active session keys from Redis."""
        sessions = self.list_sessions()
        keys_to_delete = [self._state_key(s) for s in sessions]
        keys_to_delete.append("custodian:active_sessions")
        if keys_to_delete:
            self._client.delete(*keys_to_delete)
