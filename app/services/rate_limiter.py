import time
from collections import defaultdict
from fastapi import Request, HTTPException, status

class InMemoryRateLimiter:
    """
    Simple in-memory sliding-window rate limiter for a local learning application.
    
    Limitation: State is stored process-locally and resets when the server restarts.
    """
    def __init__(self):
        # Maps key -> list of float timestamps
        self._requests = defaultdict(list)

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        timestamps = self._requests[key]
        
        # Clean up timestamps older than window
        cutoff = now - window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.pop(0)
            
        if len(timestamps) >= max_requests:
            return True
            
        timestamps.append(now)
        return False

    def check(self, key: str, max_requests: int, window_seconds: int):
        if self.is_rate_limited(key, max_requests, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(window_seconds)}
            )

    def reset(self):
        """Clears rate limiter state (useful for automated testing)."""
        self._requests.clear()

limiter = InMemoryRateLimiter()

def rate_limit(max_requests: int, window_seconds: int = 60):
    """
    FastAPI dependency for rate limiting endpoints.
    Key is determined from client IP, authorization token, and endpoint path.
    """
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        auth_header = request.headers.get("Authorization", "")
        identifier = f"{auth_header}:{client_ip}:{request.url.path}"
        limiter.check(identifier, max_requests=max_requests, window_seconds=window_seconds)
    return dependency
