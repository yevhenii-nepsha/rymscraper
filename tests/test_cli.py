"""Tests for CLI subcommands."""

from __future__ import annotations

import pytest

from rymparser.artist_parser import DEFAULT_TYPES
from rymparser.cli import (
    _parse_types,
    build_parser,
    is_artist_url,
    validate_url,
)
from rymparser.models import ReleaseType


class TestValidateUrl:
    def test_valid_rym_url(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        assert validate_url(url) is True

    def test_invalid_domain(self) -> None:
        assert validate_url("https://example.com/") is False

    def test_empty_url(self) -> None:
        assert validate_url("") is False


class TestBuildParser:
    def test_parse_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "parse",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.command == "parse"
        assert args.url == ("https://rateyourmusic.com/list/u/test/")

    def test_parse_with_output(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "parse",
                "-o",
                "out.txt",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.output == "out.txt"

    def test_search_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "search",
                "albums.txt",
            ]
        )
        assert args.command == "search"
        assert args.file == "albums.txt"

    def test_search_auto_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "search",
                "--auto",
                "albums.txt",
            ]
        )
        assert args.auto is True

    def test_download_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "download",
                "results.json",
            ]
        )
        assert args.command == "download"
        assert args.file == "results.json"

    def test_go_subcommand(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "go",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.command == "go"
        assert args.url == ("https://rateyourmusic.com/list/u/test/")

    def test_verbose_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "-v",
                "parse",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.verbose is True

    def test_config_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "--config",
                "/tmp/cfg.toml",
                "parse",
                "https://rateyourmusic.com/list/u/test/",
            ]
        )
        assert args.config == "/tmp/cfg.toml"


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


class TestBuildParserArtist:
    def test_parse_with_types_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "parse",
                "--types",
                "album,ep,live_album",
                "https://rateyourmusic.com/artist/neurosis",
            ]
        )
        assert args.types == "album,ep,live_album"

    def test_go_with_types_flag(self) -> None:
        parser = build_parser()
        args = parser.parse_args(
            [
                "go",
                "--types",
                "album",
                "https://rateyourmusic.com/artist/neurosis",
            ]
        )
        assert args.types == "album"
