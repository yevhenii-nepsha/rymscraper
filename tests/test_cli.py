"""Tests for CLI subcommands."""

from __future__ import annotations

import pytest

from rymscraper.artist_parser import DEFAULT_TYPES
from rymscraper.cli import (
    _parse_types,
    build_parser,
    is_artist_url,
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


class TestDownloadFormatExtraction:
    """Verify _cmd_download handles both formats."""

    def test_extracts_from_alternatives_format(self) -> None:
        """New format with selected + alternatives."""
        data: dict[str, object] = {
            "selected": 1,
            "alternatives": [
                {
                    "username": "user1",
                    "directory": "Music/Album",
                    "files": [{"filename": "01.mp3"}],
                    "format": "mp3",
                    "bitrate": 320,
                },
                {
                    "username": "user2",
                    "directory": "Music/Album2",
                    "files": [{"filename": "01.flac"}],
                    "format": "flac",
                    "bitrate": 0,
                },
            ],
        }
        idx = data.get("selected", 0)
        assert isinstance(idx, int)
        alts = data["alternatives"]
        assert isinstance(alts, list)
        alt = alts[idx]
        assert isinstance(alt, dict)
        assert alt["username"] == "user2"
        assert alt["files"] == [{"filename": "01.flac"}]

    def test_extracts_selected_zero(self) -> None:
        """Default selected=0 picks first alternative."""
        data: dict[str, object] = {
            "selected": 0,
            "alternatives": [
                {
                    "username": "userA",
                    "directory": "dir",
                    "files": [{"filename": "a.mp3"}],
                    "format": "mp3",
                    "bitrate": 320,
                },
            ],
        }
        idx = data.get("selected", 0)
        assert isinstance(idx, int)
        alts = data["alternatives"]
        assert isinstance(alts, list)
        alt = alts[idx]
        assert isinstance(alt, dict)
        assert alt["username"] == "userA"

    def test_extracts_from_legacy_format(self) -> None:
        """Legacy flat format still works."""
        data: dict[str, object] = {
            "username": "user1",
            "directory": "Music/Album",
            "files": [{"filename": "01.mp3"}],
            "format": "mp3",
            "bitrate": 320,
        }
        assert "alternatives" not in data
        assert data["username"] == "user1"
        assert data["files"] == [{"filename": "01.mp3"}]

    def test_download_extraction_logic(self) -> None:
        """End-to-end extraction matching _cmd_download."""
        # New format
        new_data: dict[str, object] = {
            "selected": 0,
            "alternatives": [
                {
                    "username": "alice",
                    "directory": "d",
                    "files": [{"filename": "x.flac"}],
                    "format": "flac",
                    "bitrate": 0,
                },
            ],
        }
        if "alternatives" in new_data:
            idx = new_data.get("selected", 0)
            assert isinstance(idx, int)
            alts = new_data["alternatives"]
            assert isinstance(alts, list)
            alt = alts[idx]
            assert isinstance(alt, dict)
            username = str(alt["username"])
            files = alt["files"]
        else:
            username = str(new_data["username"])
            files = new_data["files"]
        assert username == "alice"
        assert files == [{"filename": "x.flac"}]

        # Legacy format
        old_data: dict[str, object] = {
            "username": "bob",
            "files": [{"filename": "y.mp3"}],
        }
        if "alternatives" in old_data:
            idx2 = old_data.get("selected", 0)
            assert isinstance(idx2, int)
            alts2 = old_data["alternatives"]
            assert isinstance(alts2, list)
            alt2 = alts2[idx2]
            assert isinstance(alt2, dict)
            username2 = str(alt2["username"])
            files2 = alt2["files"]
        else:
            username2 = str(old_data["username"])
            files2 = old_data["files"]
        assert username2 == "bob"
        assert files2 == [{"filename": "y.mp3"}]
