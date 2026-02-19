"""Tests for browser module (unit-testable parts only)."""

from rymparser.browser import is_cloudflare_challenge


class TestIsCloudflareChallenge:
    def test_detects_cloudflare(self) -> None:
        assert is_cloudflare_challenge("Just a moment...") is True

    def test_detects_lowercase(self) -> None:
        assert is_cloudflare_challenge("just a moment") is True

    def test_normal_title(self) -> None:
        assert is_cloudflare_challenge("Best Albums of 2024") is False

    def test_empty_title(self) -> None:
        assert is_cloudflare_challenge("") is False
