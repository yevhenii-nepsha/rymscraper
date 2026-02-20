"""Tests for CLI argument parsing and validation."""

from __future__ import annotations

import pytest

from rymscraper.artist_parser import DEFAULT_TYPES
from rymscraper.cli import (
    _parse_types,
    is_artist_url,
    parse_args,
    validate_url,
)
from rymscraper.models import ReleaseType


class TestValidateUrl:
    def test_valid_rym_url(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        assert validate_url(url) is True

    def test_invalid_domain(self) -> None:
        assert validate_url("https://example.com/") is False

    def test_empty_url(self) -> None:
        assert validate_url("") is False


class TestParseArgs:
    def test_minimal_args(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args([url])
        assert args.url == url
        assert args.output is None
        assert args.headless is False
        assert args.verbose is False

    def test_output_flag(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args(["-o", "out.txt", url])
        assert args.output == "out.txt"

    def test_headless_flag(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args(["--headless", url])
        assert args.headless is True

    def test_verbose_flag(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args(["-v", url])
        assert args.verbose is True

    def test_types_flag(self) -> None:
        url = "https://rateyourmusic.com/artist/neurosis"
        args = parse_args(["--types", "album,ep", url])
        assert args.types == "album,ep"

    def test_types_default_none(self) -> None:
        url = "https://rateyourmusic.com/artist/neurosis"
        args = parse_args([url])
        assert args.types is None


class TestIsArtistUrl:
    def test_artist_url(self) -> None:
        url = "https://rateyourmusic.com/artist/neurosis"
        assert is_artist_url(url) is True

    def test_list_url(self) -> None:
        url = "https://rateyourmusic.com/list/user/my-list"
        assert is_artist_url(url) is False

    def test_artist_url_trailing_slash(self) -> None:
        url = "https://rateyourmusic.com/artist/neurosis/"
        assert is_artist_url(url) is True


class TestParseTypes:
    def test_valid_types(self) -> None:
        result = _parse_types("album,ep")
        assert result == frozenset(
            {
                ReleaseType.ALBUM,
                ReleaseType.EP,
            }
        )

    def test_none_returns_default(self) -> None:
        assert _parse_types(None) == DEFAULT_TYPES

    def test_single_type(self) -> None:
        result = _parse_types("album")
        assert result == frozenset({ReleaseType.ALBUM})

    def test_invalid_type_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_types("album,foo")

    def test_strips_whitespace(self) -> None:
        result = _parse_types("album , ep")
        assert result == frozenset(
            {
                ReleaseType.ALBUM,
                ReleaseType.EP,
            }
        )
