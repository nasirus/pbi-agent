from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pbi_agent.auth.models import (
    ProviderAuthStatus,
    RequestAuthConfig,
    StoredAuthSession,
)


class AuthProviderBackend(ABC):
    @property
    @abstractmethod
    def backend_id(self) -> str:
        """Stable backend ID stored with sessions."""

    @abstractmethod
    def build_status(self, session: StoredAuthSession | None) -> ProviderAuthStatus:
        """Return a normalized auth status view for this backend."""

    @abstractmethod
    def import_session(
        self,
        *,
        provider_id: str,
        payload: dict[str, Any],
        previous: StoredAuthSession | None = None,
    ) -> StoredAuthSession:
        """Build a stored session from a user-supplied payload."""

    @abstractmethod
    def refresh_session(self, session: StoredAuthSession) -> StoredAuthSession:
        """Refresh the current auth session."""

    @abstractmethod
    def build_request_auth(
        self,
        *,
        request_url: str,
        session: StoredAuthSession,
    ) -> RequestAuthConfig:
        """Return the request URL and auth headers for a provider call."""
