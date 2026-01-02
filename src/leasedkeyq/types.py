"""Type definitions for leasedkeyq."""

from typing import Literal, TypeAlias, TypeVar

# Generic type variables for keys and values
K = TypeVar("K")  # Key type
V = TypeVar("V")  # Value type

# Policy for handling puts when key is in-flight
InFlightPolicy: TypeAlias = Literal["update", "reject", "buffer"]
