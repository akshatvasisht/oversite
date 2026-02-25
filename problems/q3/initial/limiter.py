import time
from collections import deque

class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        # TODO: Initialize storage for request timestamps per IP
        self.history = {}

    def is_allowed(self, ip: str) -> bool:
        """
        Calculates if a request from the given IP is allowed 
        based on the sliding window limit.
        """
        now = time.time()
        # TODO: Implement sliding window logic
        return True
