"""Tests for browser module (unit-testable parts only)."""

from unittest.mock import MagicMock

import pytest

from rymscraper.browser import _wait_for_content, is_cloudflare_challenge
from rymscraper.config import ScraperConfig
from rymscraper.models import ReleaseType


class TestIsCloudflareChallenge:
    def test_detects_cloudflare(self) -> None:
        assert is_cloudflare_challenge("Just a moment...") is True

    def test_detects_lowercase(self) -> None:
        assert is_cloudflare_challenge("just a moment") is True

    def test_normal_title(self) -> None:
        assert is_cloudflare_challenge("Best Albums of 2024") is False

    def test_empty_title(self) -> None:
        assert is_cloudflare_challenge("") is False


@pytest.fixture()
def mock_page() -> MagicMock:
    """Create a mock Playwright page."""
    return MagicMock()


@pytest.fixture()
def config() -> ScraperConfig:
    """Create a default scraper config."""
    return ScraperConfig()


def test_wait_for_content_custom_selector(
    mock_page: MagicMock,
    config: ScraperConfig,
) -> None:
    """Custom selector is used instead of config default."""
    mock_page.wait_for_selector.return_value = True
    result = _wait_for_content(
        mock_page,
        config,
        selector=".custom_selector",
    )
    assert result is True
    mock_page.wait_for_selector.assert_called_once()
    call_args = mock_page.wait_for_selector.call_args
    assert call_args[0][0] == ".custom_selector"


def test_expand_sections_clicks_show_all(
    mock_page: MagicMock,
) -> None:
    """Clicks 'Show all' button when present."""
    from rymscraper.browser import _expand_sections

    mock_btn = MagicMock()
    mock_page.query_selector.return_value = mock_btn

    _expand_sections(
        mock_page,
        frozenset({ReleaseType.ALBUM}),
    )

    mock_page.query_selector.assert_called_once_with(
        "#disco_type_s span.disco_expand_section_link"
    )
    mock_btn.click.assert_called_once()


def test_expand_sections_skips_when_no_button(
    mock_page: MagicMock,
) -> None:
    """Skips section when no 'Show all' button found."""
    from rymscraper.browser import _expand_sections

    mock_page.query_selector.return_value = None

    _expand_sections(
        mock_page,
        frozenset({ReleaseType.EP}),
    )

    mock_page.query_selector.assert_called_once_with(
        "#disco_type_e span.disco_expand_section_link"
    )
    # No click should happen
