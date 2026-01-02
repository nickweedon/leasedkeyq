"""leasedkeyq - Async Keyed Leased Queue with FIFO semantics and O(1) operations."""

from leasedkeyq.core import LeasedKeyQueue
from leasedkeyq.errors import (
    InvalidLeaseError,
    KeyAlreadyInFlightError,
    LeaseAlreadyAcknowledgedError,
    LeasedKeyQError,
    QueueClosedError,
)
from leasedkeyq.lease import Lease, LeaseRecord
from leasedkeyq.types import InFlightPolicy

__version__ = "0.0.1"

__all__ = [
    "LeasedKeyQueue",
    "Lease",
    "LeaseRecord",
    "LeasedKeyQError",
    "KeyAlreadyInFlightError",
    "InvalidLeaseError",
    "LeaseAlreadyAcknowledgedError",
    "QueueClosedError",
    "InFlightPolicy",
]
