class NetworkError(Exception):
    """Base class for all network-layer errors."""


class AuthError(NetworkError):
    """Raised when IAAA authentication fails."""

    def __init__(self, code: str = "", msg: str = "Authentication failed"):
        self.code = code
        self.msg = msg
        super().__init__(f"[{code}] {msg}" if code else msg)


class TokenExpiredError(AuthError):
    """Raised when the session token has expired."""


class ConnectionError(NetworkError):
    """Raised when the network request cannot be completed."""


class ParseError(NetworkError):
    """Raised when the server response cannot be parsed."""


class SyncError(NetworkError):
    """Raised when a sync operation fails after authentication."""
