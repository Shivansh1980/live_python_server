import hmac
import secrets


class AdminAuthService:
    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    @property
    def enabled(self) -> bool:
        return bool(self._username and self._password)

    def verify(self, username: str, password: str) -> bool:
        if not self.enabled:
            return False
        username_matches = hmac.compare_digest(username, self._username)
        password_matches = hmac.compare_digest(password, self._password)
        return username_matches and password_matches

    @staticmethod
    def new_csrf_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def verify_csrf(expected: str, supplied: str) -> bool:
        return bool(expected and supplied) and hmac.compare_digest(
            expected,
            supplied,
        )
