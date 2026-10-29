"""Exceptions raised by the ZapZap SDK."""


class ZapZapError(Exception):
    """Raised when the ZapZap API returns a non-2xx response or a request fails.

    Attributes:
        message: Human readable error message (from the API body when available).
        status_code: HTTP status code, or None if the request never completed.
        response: The parsed response body (dict/list/str), or None.
    """

    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response

    def __str__(self):
        if self.status_code is not None:
            return "[{}] {}".format(self.status_code, self.message)
        return self.message
