from src.backend.api_gateway.rate_limiter import RateLimiter, _normalize_path


def test_normalize_path_collapses_uuid_and_numeric_segments():
    assert _normalize_path(
        "/api/v1/patients/12345678-1234-1234-1234-123456789abc/encounters/42"
    ) == "/api/v1/patients/:id/encounters/:id"


def test_user_specific_resources_share_a_bounded_rate_limit_bucket():
    limiter = RateLimiter()

    limiter._check_local(
        "provider-1",
        "provider",
        _normalize_path("/api/v1/patients/11111111-1111-1111-1111-111111111111"),
        10,
        20,
    )
    limiter._check_local(
        "provider-1",
        "provider",
        _normalize_path("/api/v1/patients/22222222-2222-2222-2222-222222222222"),
        10,
        20,
    )

    assert len(limiter._buckets["provider-1"]) == 1
