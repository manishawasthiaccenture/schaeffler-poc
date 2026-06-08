"""Session/workflow-state store (FR-9). Interface-backed: in-memory now, Redis/Postgres later."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from .models import SessionState


class SessionStore(ABC):
    @abstractmethod
    def create(self, conversation_id: str | None = None) -> SessionState:
        """Create a new session (generates an id if none given)."""

    @abstractmethod
    def get(self, conversation_id: str) -> SessionState | None:
        """Return the session, or None if it does not exist."""

    @abstractmethod
    def save(self, state: SessionState) -> None:
        """Persist the session state."""


class InMemorySessionStore(SessionStore):
    def __init__(self) -> None:
        self._store: dict[str, SessionState] = {}

    def create(self, conversation_id: str | None = None) -> SessionState:
        cid = conversation_id or uuid.uuid4().hex
        state = SessionState(conversation_id=cid)
        self._store[cid] = state
        return state

    def get(self, conversation_id: str) -> SessionState | None:
        return self._store.get(conversation_id)

    def save(self, state: SessionState) -> None:
        self._store[state.conversation_id] = state
