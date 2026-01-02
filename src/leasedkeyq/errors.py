"""Exception classes for leasedkeyq."""


class LeasedKeyQError(Exception):
    """Base exception for all leasedkeyq errors."""


class KeyAlreadyInFlightError(LeasedKeyQError):
    """Raised when attempting to put a key that is currently in-flight with if_in_flight='reject'."""


class InvalidLeaseError(LeasedKeyQError):
    """Raised when an invalid or unknown lease token is provided."""


class LeaseAlreadyAcknowledgedError(LeasedKeyQError):
    """Raised when attempting to ack or release a lease that was already acknowledged."""


class QueueClosedError(LeasedKeyQError):
    """Raised when operations are attempted on a closed queue."""
