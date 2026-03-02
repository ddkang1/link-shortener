"""
Test suite for the link shortener API.
Covers happy paths, error paths, and edge cases (15+ tests).
"""
import re
from datetime import datetime

import pytest


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------

def test_shorten_valid_url(client):
    """Shortening a valid URL returns a short_code and short_url."""
    res = client.post("/shorten", json={"url": "https://example.com"})
    assert res.status_code == 200
    data = res.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["short_code"] in data["short_url"]


def test_redirect_returns_302(client):
    """GET /{short_code} returns a 302 redirect to the original URL."""
    res = client.post("/shorten", json={"url": "https://example.com/redirect-test"})
    code = res.json()["short_code"]

    res2 = client.get(f"/{code}", follow_redirects=False)
    assert res2.status_code == 302
    assert res2.headers["location"] == "https://example.com/redirect-test"


def test_stats_for_valid_short_code(client):
    """GET /stats/{short_code} returns full stats for a known code."""
    res = client.post("/shorten", json={"url": "https://example.com/stats-test"})
    code = res.json()["short_code"]

    res2 = client.get(f"/stats/{code}")
    assert res2.status_code == 200
    data = res2.json()
    assert data["original_url"] == "https://example.com/stats-test"
    assert data["short_code"] == code
    assert "click_count" in data
    assert "created_at" in data


def test_click_count_increments_on_redirect(client):
    """Each redirect increments click_count by 1."""
    res = client.post("/shorten", json={"url": "https://example.com/click-test"})
    code = res.json()["short_code"]

    for i in range(3):
        client.get(f"/{code}", follow_redirects=False)

    stats = client.get(f"/stats/{code}").json()
    assert stats["click_count"] == 3


def test_multiple_urls_can_be_shortened(client):
    """Multiple distinct URLs can be shortened and looked up independently."""
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://openai.com/blog",
    ]
    codes = set()
    for url in urls:
        res = client.post("/shorten", json={"url": url})
        assert res.status_code == 200
        codes.add(res.json()["short_code"])

    assert len(codes) == 3, "Each URL should get a unique short code"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------

def test_shorten_invalid_url_format_returns_422(client):
    """Posting a non-URL string returns 422."""
    res = client.post("/shorten", json={"url": "not-a-url"})
    assert res.status_code == 422


def test_shorten_private_ip_returns_400(client):
    """URLs pointing to private IPs (127.x) are rejected with 400."""
    res = client.post("/shorten", json={"url": "http://127.0.0.1/secret"})
    assert res.status_code == 400


def test_shorten_loopback_ip_10x_returns_400(client):
    """URLs pointing to 10.x.x.x are rejected with 400."""
    res = client.post("/shorten", json={"url": "http://10.0.0.1/internal"})
    assert res.status_code == 400


def test_shorten_link_local_returns_400(client):
    """URLs pointing to 169.254.x.x (link-local) are rejected with 400."""
    res = client.post("/shorten", json={"url": "http://169.254.1.1/metadata"})
    assert res.status_code == 400


def test_redirect_nonexistent_code_returns_404(client):
    """GET /{short_code} returns 404 for an unknown short code."""
    res = client.get("/nonexistentcode123", follow_redirects=False)
    assert res.status_code == 404


def test_stats_nonexistent_code_returns_404(client):
    """GET /stats/{short_code} returns 404 for an unknown short code."""
    res = client.get("/stats/doesnotexist")
    assert res.status_code == 404


def test_shorten_missing_url_field_returns_422(client):
    """POST /shorten with an empty body returns 422."""
    res = client.post("/shorten", json={})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_same_url_twice_gets_different_codes(client):
    """Shortening the same URL twice produces two distinct short codes."""
    url = "https://example.com/same-url"
    code1 = client.post("/shorten", json={"url": url}).json()["short_code"]
    code2 = client.post("/shorten", json={"url": url}).json()["short_code"]
    assert code1 != code2


def test_click_count_starts_at_zero(client):
    """A newly created short link has click_count == 0."""
    res = client.post("/shorten", json={"url": "https://example.com/zero-clicks"})
    code = res.json()["short_code"]
    stats = client.get(f"/stats/{code}").json()
    assert stats["click_count"] == 0


def test_created_at_is_valid_timestamp(client):
    """created_at in stats response is a parseable ISO 8601 timestamp."""
    res = client.post("/shorten", json={"url": "https://example.com/ts-test"})
    code = res.json()["short_code"]
    stats = client.get(f"/stats/{code}").json()
    # Should not raise
    dt = datetime.fromisoformat(stats["created_at"].replace("Z", "+00:00"))
    assert dt.year >= 2024


def test_short_code_is_url_safe(client):
    """Generated short codes contain only URL-safe characters."""
    codes = []
    for i in range(5):
        res = client.post("/shorten", json={"url": f"https://example.com/urlsafe-{i}"})
        codes.append(res.json()["short_code"])

    url_safe_pattern = re.compile(r"^[A-Za-z0-9_\-]+$")
    for code in codes:
        assert url_safe_pattern.match(code), f"Code '{code}' is not URL-safe"


def test_very_long_url_is_handled(client):
    """A very long URL can be shortened without errors."""
    long_url = "https://example.com/" + "a" * 2000
    res = client.post("/shorten", json={"url": long_url})
    assert res.status_code == 200
    code = res.json()["short_code"]
    stats = client.get(f"/stats/{code}").json()
    assert stats["original_url"] == long_url
