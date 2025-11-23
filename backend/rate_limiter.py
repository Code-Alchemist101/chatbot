import time
from collections import defaultdict
from threading import Lock
from config import RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW

class RateLimiter:
    """Simple in-memory rate limiter using sliding window"""
    
    def __init__(self, max_requests=RATE_LIMIT_REQUESTS, window_seconds=RATE_LIMIT_WINDOW):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)
        self.lock = Lock()
    
    def is_allowed(self, key):
        """Check if request is allowed for given key (e.g., session_id)"""
        with self.lock:
            now = time.time()
            
            # Remove old requests outside the window
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.window_seconds
            ]
            
            # Check if under limit
            if len(self.requests[key]) < self.max_requests:
                self.requests[key].append(now)
                return True
            
            return False
    
    def get_remaining(self, key):
        """Get remaining requests for key"""
        with self.lock:
            now = time.time()
            self.requests[key] = [
                req_time for req_time in self.requests[key]
                if now - req_time < self.window_seconds
            ]
            return max(0, self.max_requests - len(self.requests[key]))
    
    def cleanup_old_keys(self):
        """Remove keys with no recent requests (call periodically)"""
        with self.lock:
            now = time.time()
            keys_to_remove = []
            
            for key, timestamps in self.requests.items():
                # Remove timestamps outside window
                timestamps[:] = [t for t in timestamps if now - t < self.window_seconds]
                
                # Mark key for removal if no recent requests
                if not timestamps:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.requests[key]

# Global rate limiter instance
rate_limiter = RateLimiter()
