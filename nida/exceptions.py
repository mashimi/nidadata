"""Exceptions raised by the nida package."""


class NidaError(Exception):
    """Base class for all nida errors."""


class NidaConnectionError(NidaError):
    """The request to NIDA servers failed (network error, timeout, ...)."""


class NidaInvalidIDError(NidaError):
    """The provided national ID is not in a valid format."""


class NidaNotFoundError(NidaError):
    """NIDA has no record for the provided national ID."""


__all__ = [
    "NidaError",
    "NidaConnectionError",
    "NidaInvalidIDError",
    "NidaNotFoundError",
]
