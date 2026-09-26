"""Bound local generation work. Single-process by design; limits are configurable."""
import os
import time
import threading
from collections import deque

_lock = threading.Lock()
_requests = {}
slots = threading.BoundedSemaphore(4)


def allow(address):
    try:
        maximum = max(1, min(10000, int(os.getenv("GENERATION_LIMIT_PER_HOUR", "20"))))
    except ValueError:
        maximum = 20
    now = time.monotonic()
    with _lock:
        for key in list(_requests):
            q = _requests[key]
            while q and q[0] < now-3600:
                q.popleft()
            if not q:
                del _requests[key]
        if len(_requests) >= 2048 and address not in _requests:
            return False
        q = _requests.setdefault(address, deque())
        if len(q) >= maximum:
            return False
        q.append(now)
        return True


def reset():
    with _lock:
        _requests.clear()
