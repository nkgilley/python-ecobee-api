"""Errors used in this library."""


class EcobeeError(Exception):
    """Base class for all ecobee exceptions."""

    pass


class ExpiredTokenError(EcobeeError):
    """Raised when ecobee API returns a code indicating expired credentials."""

    pass


class InvalidTokenError(EcobeeError):
    """Raised when ecobee API returns a code indicating invalid credentials."""

class InvalidSensorError(EcobeeError):
    """Raised when remote sensor not present on thermostat."""


class EcobeeAuthFailedError(EcobeeError):
    """Raised when ecobee Auth0 rejects the supplied credentials or OTP code."""

    pass


class EcobeeAuthUnknownError(EcobeeError):
    """Raised when ecobee Auth0 returns an unexpected response shape."""

    pass


class EcobeeAuthMfaRequiredError(EcobeeError):
    """Raised when ecobee Auth0 redirects to an MFA challenge during login.

    Carries an :class:`~pyecobee.MfaChallenge` payload (in ``args[0]``) that
    must be passed back into :meth:`Ecobee.submit_mfa_code` along with the
    user-entered OTP code to resume the login flow.
    """

    pass