"""Per-client limit on the endpoints that spend LLM quota, for the public demo."""
import re
import time
from collections import defaultdict, deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

LIMITED_PATHS = re.compile(r"^/api/(chat$|bids/[^/]+/(analyze|generate|responses))")


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float = 3600.0) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        hits = self._hits[key]
        while hits and current - hits[0] >= self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(current)
        return True


class LLMRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int) -> None:
        super().__init__(app)
        self._limiter = SlidingWindowLimiter(limit)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "POST" and LIMITED_PATHS.match(request.url.path):
            forwarded = request.headers.get("x-forwarded-for", "")
            client = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
            if not self._limiter.allow(client):
                return JSONResponse(
                    status_code=429,
                    content={"detail": "The public demo's hourly limit was reached. Please try again later."},
                )
        return await call_next(request)
