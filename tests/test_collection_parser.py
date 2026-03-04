"""Tests for collection page parser."""

import os
from pathlib import Path

import pytest

from rymscraper.collection_parser import (
    extract_collection_slug,
    parse_collection_page,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def collection_html() -> str:
    """Minimal RYM collection page HTML fixture."""
    return (FIXTURES / "collection_page.html").read_text()


def test_parse_collection_page_extracts_albums(
    collection_html: str,
) -> None:
    """Extracts correct number of albums."""
    albums = parse_collection_page(collection_html)
    assert len(albums) == 2


def test_parse_collection_page_artist_and_title(
    collection_html: str,
) -> None:
    """Extracts artist name and album title."""
    albums = parse_collection_page(collection_html)
    assert albums[0].artist == "Bathory"
    assert albums[0].title == "Bathory"
    assert albums[1].artist == "Burzum"
    assert albums[1].title == "Filosofem"


def test_parse_collection_page_year(
    collection_html: str,
) -> None:
    """Extracts 4-digit year from smallgray span."""
    albums = parse_collection_page(collection_html)
    assert albums[0].year == "1984"
    assert albums[1].year == "1996"


def test_parse_collection_page_empty_html() -> None:
    """Returns empty list for empty HTML."""
    assert parse_collection_page("") == []


def test_parse_collection_page_no_items() -> None:
    """Returns empty list when no collection items."""
    html = "<html><body><div>No data</div></body></html>"
    assert parse_collection_page(html) == []


def test_parse_collection_page_missing_year() -> None:
    """Returns empty year when span.smallgray absent."""
    html = (FIXTURES / "collection_missing_year.html").read_text()
    albums = parse_collection_page(html)
    assert len(albums) == 1
    assert albums[0].artist == "Darkthrone"
    assert albums[0].title == "Transilvanian Hunger"
    assert albums[0].year == ""


def test_extract_collection_slug_with_rating() -> None:
    """Extracts slug from rating-filtered URL."""
    url = "https://rateyourmusic.com/collection/stonepig/r5.0"
    slug = extract_collection_slug(url)
    assert "stonepig" in slug
    assert "collection" not in slug


def test_extract_collection_slug_strips_page() -> None:
    """Strips trailing page number from slug."""
    url = "https://rateyourmusic.com/collection/stonepig/r5.0/2"
    base_url = "https://rateyourmusic.com/collection/stonepig/r5.0"
    assert extract_collection_slug(url) == (extract_collection_slug(base_url))


def test_extract_collection_slug_bare() -> None:
    """Extracts slug from bare collection URL."""
    url = "https://rateyourmusic.com/collection/stonepig/"
    slug = extract_collection_slug(url)
    assert slug == "stonepig"


_COLLECTION_HTML = "/tmp/rym_collection_stonepig.html"


@pytest.mark.skipif(
    not os.path.exists(_COLLECTION_HTML),
    reason="Real HTML file not available",
)
def test_parse_real_collection_page() -> None:
    """Smoke test with real collection page HTML."""
    html = Path(_COLLECTION_HTML).read_text()
    albums = parse_collection_page(html)

    assert len(albums) > 0
    assert all(a.artist for a in albums)
    assert all(a.title for a in albums)
