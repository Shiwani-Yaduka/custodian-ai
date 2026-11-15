"""StateStore Interface and In-Memory Implementation for Custodian AI.

Enables pure Python session risk persistence with zero external infrastructure.
Swappable with Redis in Phase B without touching risk business logic.
"""

from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Dict, List, Optional

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
