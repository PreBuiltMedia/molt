from app.core.rate_limit import InMemoryRateLimiter


def test_rate_limit_allows_up_to_limit():
    limiter = InMemoryRateLimiter()
    for _ in range(5):
        result = limiter.check_and_record("acct1", "search", limit=5, window_seconds=60)
        assert result.allowed is True

    blocked = limiter.check_and_record("acct1", "search", limit=5, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.remaining == 0


def test_rate_limit_unlimited_when_limit_is_none():
    limiter = InMemoryRateLimiter()
    for _ in range(1000):
        result = limiter.check_and_record("acct1", "enrich", limit=None, window_seconds=60)
        assert result.allowed is True


def test_rate_limit_separate_accounts_dont_interfere():
    limiter = InMemoryRateLimiter()
    for _ in range(5):
        limiter.check_and_record("acct1", "search", limit=5, window_seconds=60)

    result = limiter.check_and_record("acct2", "search", limit=5, window_seconds=60)
    assert result.allowed is True
