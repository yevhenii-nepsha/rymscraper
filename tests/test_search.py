"""Tests for search filtering and ranking logic."""

from __future__ import annotations

from rymscraper.models import Album
from rymscraper.search import (
    AlbumSearchResult,
    _file_ext,
    build_query,
    filter_responses,
    rank_results,
)
from rymscraper.settings import AppSettings


def _make_response(
    username: str,
    files: list[dict[str, object]],
    *,
    free_slot: bool = True,
    speed: int = 1_000_000,
    queue: int = 0,
) -> dict[str, object]:
    """Build a mock slskd search response."""
    return {
        "username": username,
        "files": files,
        "hasFreeUploadSlot": free_slot,
        "uploadSpeed": speed,
        "queueLength": queue,
        "fileCount": len(files),
        "lockedFileCount": 0,
        "lockedFiles": [],
        "token": 1,
    }


def _make_file(
    name: str,
    ext: str = "flac",
    size: int = 30_000_000,
    bitrate: int = 1411,
) -> dict[str, object]:
    """Build a mock slskd file object."""
    return {
        "filename": f"@@user\\Music\\Artist\\{name}",
        "size": size,
        "extension": ext,
        "bitRate": bitrate,
        "length": 240,
        "sampleRate": 44100,
        "code": 1,
        "isLocked": False,
    }


class TestFileExt:
    def test_uses_extension_field(self) -> None:
        f = {"extension": "flac", "filename": "x.flac"}
        assert _file_ext(f) == "flac"

    def test_falls_back_to_filename(self) -> None:
        """When extension is empty, extract from filename."""
        f = {"extension": "", "filename": "01 - Track.flac"}
        assert _file_ext(f) == "flac"

    def test_empty_extension_mp3(self) -> None:
        f = {"extension": "", "filename": "song.mp3"}
        assert _file_ext(f) == "mp3"

    def test_no_extension_no_dot(self) -> None:
        f = {"extension": "", "filename": "README"}
        assert _file_ext(f) == ""

    def test_normalizes_dot_prefix(self) -> None:
        f = {"extension": ".FLAC", "filename": "x"}
        assert _file_ext(f) == "flac"


class TestBuildQuery:
    def test_strips_year(self) -> None:
        album = Album("Radiohead", "OK Computer", "1997")
        assert build_query(album) == "Radiohead OK Computer"

    def test_no_year(self) -> None:
        album = Album("Bjork", "Homogenic", "")
        assert build_query(album) == "Bjork Homogenic"


class TestFilterResponses:
    def test_filters_by_format(self) -> None:
        responses = [
            _make_response(
                "u1",
                [
                    _make_file("01.flac", "flac"),
                    _make_file("02.flac", "flac"),
                    _make_file("03.flac", "flac"),
                ],
            ),
            _make_response(
                "u2",
                [
                    _make_file("01.wma", "wma", bitrate=128),
                    _make_file("02.wma", "wma", bitrate=128),
                    _make_file("03.wma", "wma", bitrate=128),
                ],
            ),
        ]
        settings = AppSettings(
            preferred_formats=["flac", "mp3"],
            min_bitrate=320,
            min_files=3,
        )
        results = filter_responses(responses, settings)
        assert len(results) == 1
        assert results[0].username == "u1"

    def test_filters_by_min_files(self) -> None:
        responses = [
            _make_response(
                "u1",
                [_make_file("01.flac", "flac")],
            ),
        ]
        settings = AppSettings(min_files=3)
        results = filter_responses(responses, settings)
        assert len(results) == 0

    def test_mp3_must_meet_min_bitrate(self) -> None:
        responses = [
            _make_response(
                "u1",
                [
                    _make_file("01.mp3", "mp3", bitrate=128),
                    _make_file("02.mp3", "mp3", bitrate=128),
                    _make_file("03.mp3", "mp3", bitrate=128),
                ],
            ),
        ]
        settings = AppSettings(
            preferred_formats=["flac", "mp3"],
            min_bitrate=320,
            min_files=3,
        )
        results = filter_responses(responses, settings)
        assert len(results) == 0

    def test_empty_extension_uses_filename(self) -> None:
        """Real slskd bug: extension="" but filename has ext."""
        responses = [
            _make_response(
                "u1",
                [
                    {
                        "filename": "Music\\Artist\\01.flac",
                        "size": 30_000_000,
                        "extension": "",
                        "bitDepth": 16,
                        "sampleRate": 44100,
                        "length": 240,
                        "code": 1,
                        "isLocked": False,
                    },
                    {
                        "filename": "Music\\Artist\\02.flac",
                        "size": 30_000_000,
                        "extension": "",
                        "bitDepth": 16,
                        "sampleRate": 44100,
                        "length": 240,
                        "code": 1,
                        "isLocked": False,
                    },
                ],
            ),
        ]
        settings = AppSettings(
            preferred_formats=["flac", "mp3"],
            min_files=1,
        )
        results = filter_responses(responses, settings)
        assert len(results) == 1
        assert results[0].format == "flac"

    def test_mp3_320_passes(self) -> None:
        responses = [
            _make_response(
                "u1",
                [
                    _make_file(
                        "01.mp3",
                        "mp3",
                        bitrate=320,
                        size=10_000_000,
                    ),
                    _make_file(
                        "02.mp3",
                        "mp3",
                        bitrate=320,
                        size=10_000_000,
                    ),
                    _make_file(
                        "03.mp3",
                        "mp3",
                        bitrate=320,
                        size=10_000_000,
                    ),
                ],
            ),
        ]
        settings = AppSettings(
            preferred_formats=["flac", "mp3"],
            min_bitrate=320,
            min_files=3,
        )
        results = filter_responses(responses, settings)
        assert len(results) == 1

    def test_rejects_wrong_album_directory(self) -> None:
        """Reject results where directory doesn't match album."""
        album = Album("Neurosis", "Locust Star", "1996")
        responses = [
            _make_response(
                "u1",
                [
                    {
                        "filename": (
                            "@@u1\\Music\\Neurosis\\"
                            "(1996) Through Silver in Blood\\"
                            "01.flac"
                        ),
                        "size": 30_000_000,
                        "extension": "flac",
                        "bitRate": 1411,
                        "length": 240,
                        "sampleRate": 44100,
                        "code": 1,
                        "isLocked": False,
                    },
                    {
                        "filename": (
                            "@@u1\\Music\\Neurosis\\"
                            "(1996) Through Silver in Blood\\"
                            "02.flac"
                        ),
                        "size": 30_000_000,
                        "extension": "flac",
                        "bitRate": 1411,
                        "length": 240,
                        "sampleRate": 44100,
                        "code": 1,
                        "isLocked": False,
                    },
                    {
                        "filename": (
                            "@@u1\\Music\\Neurosis\\"
                            "(1996) Through Silver in Blood\\"
                            "03.flac"
                        ),
                        "size": 30_000_000,
                        "extension": "flac",
                        "bitRate": 1411,
                        "length": 240,
                        "sampleRate": 44100,
                        "code": 1,
                        "isLocked": False,
                    },
                ],
            ),
        ]
        settings = AppSettings(
            preferred_formats=["flac", "mp3"],
            min_files=3,
        )
        results = filter_responses(responses, settings, album)
        assert len(results) == 0

    def test_accepts_matching_album_directory(self) -> None:
        """Accept results where directory matches album title."""
        album = Album(
            "Neurosis",
            "Through Silver in Blood",
            "1996",
        )
        responses = [
            _make_response(
                "u1",
                [
                    {
                        "filename": (
                            "@@u1\\Music\\Neurosis\\"
                            "(1996) Through Silver in Blood\\"
                            "01.flac"
                        ),
                        "size": 30_000_000,
                        "extension": "flac",
                        "bitRate": 1411,
                        "length": 240,
                        "sampleRate": 44100,
                        "code": 1,
                        "isLocked": False,
                    },
                    {
                        "filename": (
                            "@@u1\\Music\\Neurosis\\"
                            "(1996) Through Silver in Blood\\"
                            "02.flac"
                        ),
                        "size": 30_000_000,
                        "extension": "flac",
                        "bitRate": 1411,
                        "length": 240,
                        "sampleRate": 44100,
                        "code": 1,
                        "isLocked": False,
                    },
                    {
                        "filename": (
                            "@@u1\\Music\\Neurosis\\"
                            "(1996) Through Silver in Blood\\"
                            "03.flac"
                        ),
                        "size": 30_000_000,
                        "extension": "flac",
                        "bitRate": 1411,
                        "length": 240,
                        "sampleRate": 44100,
                        "code": 1,
                        "isLocked": False,
                    },
                ],
            ),
        ]
        settings = AppSettings(
            preferred_formats=["flac", "mp3"],
            min_files=3,
        )
        results = filter_responses(responses, settings, album)
        assert len(results) == 1
        assert results[0].username == "u1"


class TestRankResults:
    def test_prefers_flac_over_mp3(self) -> None:
        r_flac = AlbumSearchResult(
            username="u1",
            directory="d",
            files=[_make_file("01.flac", "flac")],
            format="flac",
            bitrate=1411,
            upload_speed=1_000_000,
            has_free_slot=True,
            queue_length=0,
        )
        r_mp3 = AlbumSearchResult(
            username="u2",
            directory="d",
            files=[
                _make_file(
                    "01.mp3",
                    "mp3",
                    bitrate=320,
                ),
            ],
            format="mp3",
            bitrate=320,
            upload_speed=1_000_000,
            has_free_slot=True,
            queue_length=0,
        )
        settings = AppSettings(
            preferred_formats=["flac", "mp3"],
        )
        ranked = rank_results([r_mp3, r_flac], settings)
        assert ranked[0].format == "flac"

    def test_prefers_free_slot(self) -> None:
        r_free = AlbumSearchResult(
            username="u1",
            directory="d",
            files=[],
            format="flac",
            bitrate=1411,
            upload_speed=500_000,
            has_free_slot=True,
            queue_length=0,
        )
        r_queued = AlbumSearchResult(
            username="u2",
            directory="d",
            files=[],
            format="flac",
            bitrate=1411,
            upload_speed=1_000_000,
            has_free_slot=False,
            queue_length=50,
        )
        settings = AppSettings(
            preferred_formats=["flac"],
        )
        ranked = rank_results(
            [r_queued, r_free],
            settings,
        )
        assert ranked[0].has_free_slot is True
