"""Project-specific exceptions."""

from __future__ import annotations


class CollisionAgentError(Exception):
    """Base exception for domain-specific failures."""

    def __init__(self, message: str, *, code: str = "collision_agent_error") -> None:
        super().__init__(message)
        self.code = code


class NotFoundError(CollisionAgentError):
    """Raised when a requested resource is missing."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="not_found")


class ValidationFailure(CollisionAgentError):
    """Raised for invalid or insufficient task input."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_failure")

