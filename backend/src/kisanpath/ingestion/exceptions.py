"""KisanPath-owned ingestion and publication errors."""


class IngestionError(Exception):
    """Base class for deterministic ingestion failures."""


class InvalidIngestionTransitionError(IngestionError):
    """Raised when a lifecycle state is skipped or revisited."""


class HumanReviewRequiredError(IngestionError):
    """Raised when an automated actor attempts a human trust transition."""


class PublicationGateError(IngestionError):
    """Raised when reviewed provenance is incomplete or inconsistent."""
