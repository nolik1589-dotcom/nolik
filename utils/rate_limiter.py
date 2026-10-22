import time
from typing import Dict

class RateLimiter:
    """Simple in-memory rate limiter per user."""

    def __init__(self, cooldown_seconds: int = 3):
        self.cooldown = cooldown_seconds
        self._last_request: Dict[int, float] = {}

    def is_allowed(self, user_id: int) -> bool:
        """Return True if user is allowed to make a request, False if rate limited."""
        now = time.time()
        last_time = self._last_request.get(user_id, 0)
        if now - last_time < self.cooldown:
            return False
        self._last_request[user_id] = now
        return True

    def time_remaining(self, user_id: int) -> int:
        """Get remaining cooldown time in seconds."""
        now = time.time()
        last_time = self._last_request.get(user_id, 0)
        remaining = self.cooldown - (now - last_time)
        return max(1, int(remaining))
