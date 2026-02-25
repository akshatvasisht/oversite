import time
from collections import deque

class RateLimiter:
    """
    A sliding-window rate limiter designed to be used as a global middleware.
    """
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self.history = {} # ip -> deque of timestamps

    def is_allowed(self, ip: str) -> bool:
        """
        Determines if the request from 'ip' should be throttled.
        """
        # TODO: Implement sliding window logic
        return True
