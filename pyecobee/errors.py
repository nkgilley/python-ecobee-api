"""Errors used in this library."""


class EcobeeError(Exception):
    """Base class for all ecobee exceptions."""

    pass


class ExpiredTokenError(EcobeeError):
    """Raised when ecobee API returns a code indicating expired credentials."""

    pass


class InvalidTokenError(EcobeeError):
    """Raised when ecobee API returns a code indicating invalid credentials."""
