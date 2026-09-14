from chat.rate_limiter import PerUserRateLimiter


def test_users_have_independent_buckets():
    limiter = PerUserRateLimiter()
    now = 1_000_000_000
    assert all(limiter.allow("alice", "button", now) for _ in range(3))
    assert not limiter.allow("alice", "button", now)
    assert limiter.allow("bob", "button", now)


def test_bucket_refills_from_monotonic_time():
    limiter = PerUserRateLimiter()
    now = 1_000_000_000
    for _ in range(3):
        limiter.allow("alice", "camera", now)
    assert limiter.allow("alice", "camera", now + 200_000_000)
