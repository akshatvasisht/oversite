## Objective
A series of high-frequency automated probes has recently targeted your public API. To prevent denial-of-service conditions, you must implement a **Sliding-Window Rate Limiter** to throttle abusive IP addresses.

## The Challenge
Unlike a "Fixed Window" which resets at rigid 10-second intervals, a **Sliding Window** ensures that a user can never send more than **5 requests in any 10-second period**, regardless of when the window started.

## Requirements
1.  **Middleware Logic**: Complete the `RateLimiter` class in `limiter.py` to track request timestamps.
2.  **IP-Based Throttling**: Use `request.remote_addr` to uniquely identify the source of each request.
3.  **HTTP Compliance**:
    - If the limit is exceeded, return an **HTTP 429 Too Many Requests** error.
    - The error response should be a JSON object: `{"error": "Rate limit exceeded"}`.
4.  **Performance**: Your implementation should be efficient; only store as many timestamps as are needed to calculate the window.

## Example Scenario
- **0.0s**: User A (IP `1.1.1.1`) sends Request 1 → **Allowed**
- **2.0s**: User A sends Request 2 → **Allowed**
- **5.0s**: User A sends Request 3 → **Allowed**
- **7.0s**: User A sends Request 4 → **Allowed**
- **9.0s**: User A sends Request 5 → **Allowed**
- **9.5s**: User A sends Request 6 → **Blocked (429)** (5 requests already sent in last 10s)
- **10.5s**: User A sends Request 7 → **Allowed** (Request 1 is now older than 10s)

## Task Breakdown
1.  **Implement the Limiter**: Write the storage and comparison logic in `limiter.py`.
2.  **Integrate with Flask**: Apply the limiter in `app.py`.
3.  **Verify**: Run `pytest tests/test_limiter.py` to confirm the sliding window logic handles edge cases correctly.
