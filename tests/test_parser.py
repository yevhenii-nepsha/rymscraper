"""Tests for HTML parsing functions."""

from pathlib import Path

import pytest

from rymparser.models import Album
from rymparser.parser import (
    extract_slug,
    find_next_page_url,
    parse_page,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def single_page_html() -> str:
    """HTML with two valid album rows."""
    return (FIXTURES / "single_page.html").read_text()


@pytest.fixture
def no_albums_html() -> str:
    """HTML with no album data."""
    return (FIXTURES / "no_albums.html").read_text()


@pytest.fixture
def missing_year_html() -> str:
    """HTML with album missing year element."""
    return (FIXTURES / "missing_year.html").read_text()


@pytest.fixture
def paginated_html() -> str:
    """HTML with a next-page link."""
    return (FIXTURES / "with_pagination.html").read_text()


@pytest.fixture
def unpaginated_html() -> str:
    """HTML without a next-page link."""
    return (FIXTURES / "no_next_page.html").read_text()


class TestParsePage:
    def test_extracts_albums(
        self,
        single_page_html: str,
    ) -> None:
        albums = parse_page(single_page_html)
        assert albums == [
            Album("Radiohead", "OK Computer", "1997"),
            Album("Björk", "Homogenic", "1997"),
        ]

    def test_empty_for_no_albums(
        self,
        no_albums_html: str,
    ) -> None:
        assert parse_page(no_albums_html) == []

    def test_missing_year(
        self,
        missing_year_html: str,
    ) -> None:
        albums = parse_page(missing_year_html)
        assert len(albums) == 1
        assert albums[0].year == ""

    def test_empty_html(self) -> None:
        assert parse_page("") == []


class TestFindNextPageUrl:
    def test_finds_navlinknext(
        self,
        paginated_html: str,
    ) -> None:
        base = "https://rateyourmusic.com/list/test/"
        url = find_next_page_url(paginated_html, base)
        assert url == ("https://rateyourmusic.com/list/test/2/")

    def test_none_when_no_next(
        self,
        unpaginated_html: str,
    ) -> None:
        base = "https://rateyourmusic.com/list/test/"
        assert (
            find_next_page_url(
                unpaginated_html,
                base,
            )
            is None
        )


class TestExtractSlug:
    def test_simple_slug(self) -> None:
        url = "https://rateyourmusic.com/list/u/best/"
        assert extract_slug(url) == "best"

    def test_skips_page_number(self) -> None:
        url = "https://rateyourmusic.com/list/u/best/2/"
        assert extract_slug(url) == "best"

    def test_fallback(self) -> None:
        url = "https://rateyourmusic.com/"
        assert extract_slug(url) == "rym_list"
