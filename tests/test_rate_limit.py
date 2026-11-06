from backend.utils.rate_limit import LIMITED_PATHS, SlidingWindowLimiter


def test_limiter_blocks_after_the_limit_and_recovers_after_the_window() -> None:
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)

    assert limiter.allow("client", now=0)
    assert limiter.allow("client", now=1)
    assert not limiter.allow("client", now=2)
    assert limiter.allow("client", now=61)


def test_limiter_tracks_clients_separately() -> None:
    limiter = SlidingWindowLimiter(limit=1, window_seconds=60)

    assert limiter.allow("first", now=0)
    assert limiter.allow("second", now=0)
    assert not limiter.allow("first", now=1)


def test_only_llm_endpoints_are_limited() -> None:
    assert LIMITED_PATHS.match("/api/chat")
    assert LIMITED_PATHS.match("/api/bids/123/analyze")
    assert not LIMITED_PATHS.match("/api/health")
    assert not LIMITED_PATHS.match("/api/bids")
