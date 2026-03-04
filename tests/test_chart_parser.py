"""Tests for chart page parser."""

import os
from pathlib import Path

import pytest

from rymscraper.chart_parser import (
    extract_chart_slug,
    parse_chart_page,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def chart_html() -> str:
    """Minimal RYM chart page HTML fixture."""
    return (FIXTURES / "chart_page.html").read_text()


def test_parse_chart_page_extracts_albums(
    chart_html: str,
) -> None:
    """Extracts correct number of albums."""
    albums = parse_chart_page(chart_html)
    assert len(albums) == 2


def test_parse_chart_page_artist_and_title(
    chart_html: str,
) -> None:
    """Extracts artist name and album title."""
    albums = parse_chart_page(chart_html)
    assert albums[0].artist == "Christian Death"
    assert albums[0].title == "Only Theatre of Pain"


def test_parse_chart_page_year(
    chart_html: str,
) -> None:
    """Extracts 4-digit year from date string."""
    albums = parse_chart_page(chart_html)
    assert albums[0].year == "1982"
    assert albums[1].year == "1983"


def test_parse_chart_page_empty_html() -> None:
    """Returns empty list for empty HTML."""
    assert parse_chart_page("") == []


def test_parse_chart_page_no_items() -> None:
    """Returns empty list when no chart items found."""
    html = "<html><body><div>No charts</div></body></html>"
    assert parse_chart_page(html) == []


def test_parse_chart_page_missing_year() -> None:
    """Returns empty year when date is missing."""
    html = (FIXTURES / "chart_missing_year.html").read_text()
    albums = parse_chart_page(html)
    assert len(albums) == 1
    assert albums[0].year == ""


def test_extract_chart_slug_genre() -> None:
    """Extracts slug with genre from chart URL."""
    url = "https://rateyourmusic.com/charts/top/album/all-time/g:deathrock/"
    slug = extract_chart_slug(url)
    assert "deathrock" in slug
    assert "charts" not in slug


def test_extract_chart_slug_with_page_number() -> None:
    """Strips trailing page number from slug."""
    url = "https://rateyourmusic.com/charts/top/album/all-time/g:deathrock/2/"
    slug = extract_chart_slug(url)
    assert slug == extract_chart_slug(
        "https://rateyourmusic.com/charts/top/album/all-time/g:deathrock/"
    )


def test_extract_chart_slug_year() -> None:
    """Extracts slug with year from chart URL."""
    url = "https://rateyourmusic.com/charts/top/album/2024/"
    slug = extract_chart_slug(url)
    assert "2024" in slug


_DEATHROCK_HTML = "/tmp/rym_chart_deathrock.html"


@pytest.mark.skipif(
    not os.path.exists(_DEATHROCK_HTML),
    reason="Real HTML file not available",
)
def test_parse_real_deathrock_chart() -> None:
    """Smoke test with real deathrock chart page HTML."""
    html = Path(_DEATHROCK_HTML).read_text()
    albums = parse_chart_page(html)

    assert len(albums) > 0
    assert all(a.artist for a in albums)
    assert all(a.title for a in albums)
    # First album should be Christian Death
    assert albums[0].artist == "Christian Death"
