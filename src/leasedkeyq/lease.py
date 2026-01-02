"""Lease management classes."""

import time
import uuid
from dataclasses import dataclass
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class Lease(Generic[K]):
    """Immutable lease token representing exclusive access to a keyed item."""

    token: str  # UUID-based unique identifier
    key: K

    @classmethod
    def create(cls, key: K) -> "Lease[K]":
        """Create a new lease with a unique token."""
        return cls(token=str(uuid.uuid4()), key=key)


@dataclass
class LeaseRecord(Generic[K, V]):
    """Internal record tracking an in-flight lease."""

    lease: Lease[K]
    key: K
    value: V
    acknowledged: bool = False
    created_at: float = 0.0  # monotonic timestamp
    timeout: float | None = None  # timeout in seconds (None = no timeout)

    def __post_init__(self) -> None:
        """Initialize created_at if not provided."""
        if self.created_at == 0.0:
            object.__setattr__(self, "created_at", time.monotonic())

    def is_expired(self, now: float) -> bool:
        """Check if the lease has expired."""
        if self.timeout is None:
            return False
        return now - self.created_at >= self.timeout
