"""Tests for CLI argument parsing and validation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from rymscraper.artist_parser import DEFAULT_TYPES
from rymscraper.cli import (
    _parse_types,
    is_artist_url,
    is_chart_url,
    parse_args,
    validate_url,
)
from rymscraper.models import ReleaseType

if TYPE_CHECKING:
    from pathlib import Path


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


class TestIsChartUrl:
    def test_chart_url(self) -> None:
        url = "https://rateyourmusic.com/charts/top/album/all-time/g:deathrock/"
        assert is_chart_url(url) is True

    def test_chart_url_with_page(self) -> None:
        url = (
            "https://rateyourmusic.com/charts/top/album/all-time/g:deathrock/2/"
        )
        assert is_chart_url(url) is True

    def test_list_url_not_chart(self) -> None:
        url = "https://rateyourmusic.com/list/user/test"
        assert is_chart_url(url) is False

    def test_artist_url_not_chart(self) -> None:
        url = "https://rateyourmusic.com/artist/neurosis"
        assert is_chart_url(url) is False


class TestSpotifyFlag:
    def test_spotify_flag_default_false(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args([url])
        assert args.spotify is False

    def test_spotify_flag_set(self) -> None:
        url = "https://rateyourmusic.com/list/u/test/"
        args = parse_args(["--spotify", url])
        assert args.spotify is True


class TestSpotifyIntegration:
    @patch("rymscraper.cli.fetch_all_pages")
    def test_spotify_filters_output(
        self,
        mock_fetch: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When --spotify, only unfound albums are written."""
        from rymscraper.models import Album

        albums = [
            Album(artist="A", title="Found", year="2000"),
            Album(artist="B", title="Missing", year="2001"),
        ]
        mock_fetch.return_value = albums
        out = tmp_path / "out.txt"

        with patch(
            "rymscraper.spotify.sync_albums_to_spotify",
        ) as mock_sync:
            mock_sync.return_value = [albums[1]]
            from rymscraper.cli import main

            main(
                [
                    "--spotify",
                    "-o",
                    str(out),
                    "https://rateyourmusic.com/list/u/test/",
                ]
            )
            mock_sync.assert_called_once()

        content = out.read_text()
        assert "Missing" in content
        assert "Found" not in content

    @patch("rymscraper.cli.fetch_all_pages")
    def test_spotify_all_found_no_txt(
        self,
        mock_fetch: MagicMock,
        tmp_path: Path,
    ) -> None:
        """When all albums found in Spotify, skip .txt."""
        from rymscraper.models import Album

        mock_fetch.return_value = [
            Album(artist="A", title="X", year="2000"),
        ]
        out = tmp_path / "out.txt"

        with patch(
            "rymscraper.spotify.sync_albums_to_spotify",
        ) as mock_sync:
            mock_sync.return_value = []
            from rymscraper.cli import main

            main(
                [
                    "--spotify",
                    "-o",
                    str(out),
                    "https://rateyourmusic.com/list/u/test/",
                ]
            )

        assert not out.exists()
