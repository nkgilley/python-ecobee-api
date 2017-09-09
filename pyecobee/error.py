class EcoBeeIOError(Exception):
    """Base class for all EcoBee API request failures."""
    pass


class RequestError(Exception):
    """General error for a failed EcoBee API request."""
    def __init__(self, response):
        super(RequestError, self).__init__("EcoBee API request failed: {0} {1}".format(
            response.status_code, response.reason))


class ThrottlingError(EcoBeeIOError):
    """Too many requests have been made to EcoBee API in a short period of time.
    Reduce the rate of requests and try again later.
    """
    def __init__(self):
        super(ThrottlingError, self).__init__("Exceeded the limit of EcoBee API "  \
            "requests in a short period of time. Please reduce the rate of requests " \
            "and try again later.")
