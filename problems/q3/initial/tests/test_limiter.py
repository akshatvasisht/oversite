import time
import pytest
from limiter import RateLimiter

def test_rate_limiter_basic():
    limiter = RateLimiter(limit=2, window_seconds=1)
    
    # 2 requests should pass
    assert limiter.is_allowed("1.1.1.1") == True
    assert limiter.is_allowed("1.1.1.1") == True
    
    # 3rd request should fail
    assert limiter.is_allowed("1.1.1.1") == False

def test_rate_limiter_window_expiry():
    limiter = RateLimiter(limit=1, window_seconds=1)
    
    assert limiter.is_allowed("2.2.2.2") == True
    assert limiter.is_allowed("2.2.2.2") == False
    
    # Wait for window to expire
    time.sleep(1.1)
    assert limiter.is_allowed("2.2.2.2") == True

def test_rate_limiter_isolation():
    limiter = RateLimiter(limit=1, window_seconds=10)
    
    assert limiter.is_allowed("3.3.3.3") == True
    # Different IP should still be allowed
    assert limiter.is_allowed("4.4.4.4") == True
