"""KisanPath-owned persistence exceptions."""


class PersistenceError(Exception):
    """Base class for persistence failures."""


class RecordNotFoundError(PersistenceError):
    """Raised when a requested record does not exist."""


class RecordAlreadyExistsError(PersistenceError):
    """Raised when a unique record already exists."""


class ConcurrentWriteError(PersistenceError):
    """Raised when optimistic concurrency detects a stale write."""
