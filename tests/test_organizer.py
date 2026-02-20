"""Tests for post-download file organization."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from rymparser.models import Album
from rymparser.organizer import (
    _album_target_dir,
    _build_dir_to_album_map,
    _organize_album,
    _source_dir_name,
    organize_downloads,
    wait_and_organize,
)


class TestSourceDirName:
    def test_windows_path(self) -> None:
        d = (
            "@@fknkb\\Library\\Bowel Erosion"
            "\\Death Is the Orgasm of Life (2023)"
        )
        assert _source_dir_name(d) == ("Death Is the Orgasm of Life (2023)")

    def test_posix_path(self) -> None:
        d = "Music/grind/organ failure/demo"
        assert _source_dir_name(d) == "demo"

    def test_single_component(self) -> None:
        assert _source_dir_name("MyAlbum") == "MyAlbum"


class TestAlbumTargetDir:
    def test_with_year(self) -> None:
        album = Album("Bowel Erosion", "Death Is the Orgasm of Life", "2023")
        result = _album_target_dir(album, Path("/dl"))
        assert result == Path(
            "/dl/Bowel Erosion/Death Is the Orgasm of Life (2023)"
        )

    def test_without_year(self) -> None:
        album = Album("Artist", "Title", "")
        result = _album_target_dir(album, Path("/dl"))
        assert result == Path("/dl/Artist/Title")


class TestOrganizeDownloads:
    def test_moves_album(self, tmp_path: Path) -> None:
        dl = tmp_path / "downloads"
        src = dl / "Death Is the Orgasm of Life (2023)"
        src.mkdir(parents=True)
        (src / "01.flac").write_text("audio")

        results = {
            "Bowel Erosion - Death Is the Orgasm of Life (2023)": {
                "directory": (
                    "Library\\Bowel Erosion\\Death Is the Orgasm of Life (2023)"
                ),
                "username": "u1",
                "files": [],
            },
        }

        moved, skipped = organize_downloads(results, dl)
        assert moved == 1
        assert skipped == 0

        target = dl / "Bowel Erosion" / "Death Is the Orgasm of Life (2023)"
        assert target.exists()
        assert (target / "01.flac").read_text() == "audio"
        assert not src.exists()

    def test_skips_null_result(self, tmp_path: Path) -> None:
        dl = tmp_path / "downloads"
        dl.mkdir()
        results = {"Artist - Album (2020)": None}
        moved, skipped = organize_downloads(results, dl)
        assert moved == 0
        assert skipped == 1

    def test_skips_missing_source(
        self,
        tmp_path: Path,
    ) -> None:
        dl = tmp_path / "downloads"
        dl.mkdir()
        results = {
            "Artist - Album (2020)": {
                "directory": "Music\\Artist\\Album",
                "username": "u1",
                "files": [],
            },
        }
        moved, skipped = organize_downloads(results, dl)
        assert moved == 0
        assert skipped == 1

    def test_skips_existing_target(
        self,
        tmp_path: Path,
    ) -> None:
        dl = tmp_path / "downloads"
        src = dl / "Album"
        src.mkdir(parents=True)
        (src / "01.flac").write_text("audio")

        target = dl / "Artist" / "Album (2020)"
        target.mkdir(parents=True)

        results = {
            "Artist - Album (2020)": {
                "directory": "Music\\Artist\\Album",
                "username": "u1",
                "files": [],
            },
        }
        moved, skipped = organize_downloads(results, dl)
        assert moved == 0
        assert skipped == 1

    def test_multiple_albums(
        self,
        tmp_path: Path,
    ) -> None:
        dl = tmp_path / "downloads"
        (dl / "Album A").mkdir(parents=True)
        (dl / "Album A" / "01.flac").write_text("a")
        (dl / "Album B").mkdir(parents=True)
        (dl / "Album B" / "01.flac").write_text("b")

        results = {
            "Artist1 - Album A (2020)": {
                "directory": "Music\\Artist1\\Album A",
                "username": "u1",
                "files": [],
            },
            "Artist2 - Album B (2021)": {
                "directory": "Music\\Artist2\\Album B",
                "username": "u2",
                "files": [],
            },
        }
        moved, skipped = organize_downloads(results, dl)
        assert moved == 2
        assert skipped == 0
        assert (dl / "Artist1" / "Album A (2020)" / "01.flac").exists()
        assert (dl / "Artist2" / "Album B (2021)" / "01.flac").exists()


class TestOrganizeAlbum:
    def test_moves_single_album(self, tmp_path: Path) -> None:
        dl = tmp_path / "downloads"
        src = dl / "Some Album (2020)"
        src.mkdir(parents=True)
        (src / "01.flac").write_text("audio")
        ok = _organize_album(
            "Artist - Some Album (2020)",
            "Music\\Artist\\Some Album (2020)",
            dl,
        )
        assert ok is True
        target = dl / "Artist" / "Some Album (2020)"
        assert target.exists()
        assert (target / "01.flac").read_text() == "audio"
        assert not src.exists()

    def test_returns_false_missing_source(
        self,
        tmp_path: Path,
    ) -> None:
        dl = tmp_path / "downloads"
        dl.mkdir()
        ok = _organize_album(
            "Artist - Album (2020)",
            "Music\\Artist\\Album",
            dl,
        )
        assert ok is False

    def test_returns_false_bad_album_str(
        self,
        tmp_path: Path,
    ) -> None:
        dl = tmp_path / "downloads"
        (dl / "Album").mkdir(parents=True)
        ok = _organize_album("bad string", "Album", dl)
        assert ok is False

    def test_returns_false_target_exists(
        self,
        tmp_path: Path,
    ) -> None:
        dl = tmp_path / "downloads"
        (dl / "Album").mkdir(parents=True)
        (dl / "Artist" / "Album (2020)").mkdir(parents=True)
        ok = _organize_album(
            "Artist - Album (2020)",
            "Music\\Artist\\Album",
            dl,
        )
        assert ok is False
        assert (dl / "Album").exists()


class TestBuildDirToAlbumMap:
    def test_builds_mapping(self) -> None:
        results = {
            "Artist - Album (2020)": {
                "directory": "Music\\Artist\\Album",
                "username": "u1",
                "files": [],
            },
            "Band - EP (2021)": {
                "directory": "@@user\\Library\\Band\\EP",
                "username": "u2",
                "files": [],
            },
        }
        mapping = _build_dir_to_album_map(results)
        assert mapping == {
            "Music/Artist/Album": (
                "Artist - Album (2020)",
                "Music\\Artist\\Album",
            ),
            "@@user/Library/Band/EP": (
                "Band - EP (2021)",
                "@@user\\Library\\Band\\EP",
            ),
        }

    def test_skips_null_results(self) -> None:
        results = {
            "Artist - Album (2020)": None,
            "Band - EP (2021)": {
                "directory": "Music\\Band\\EP",
                "username": "u1",
                "files": [],
            },
        }
        mapping = _build_dir_to_album_map(results)
        assert len(mapping) == 1
        assert "Music/Band/EP" in mapping

    def test_skips_empty_directory(self) -> None:
        results = {
            "Artist - Album (2020)": {
                "directory": "",
                "username": "u1",
                "files": [],
            },
        }
        mapping = _build_dir_to_album_map(results)
        assert len(mapping) == 0

    def test_builds_mapping_new_format(self) -> None:
        results = {
            "Artist - Album (2020)": {
                "selected": 0,
                "alternatives": [
                    {
                        "username": "u1",
                        "directory": "Music\\Artist\\Album",
                        "files": [],
                        "format": "flac",
                        "bitrate": 0,
                    },
                    {
                        "username": "u2",
                        "directory": "Music\\Artist\\Album2",
                        "files": [],
                        "format": "mp3",
                        "bitrate": 320,
                    },
                ],
            },
        }
        mapping = _build_dir_to_album_map(results)
        assert "Music/Artist/Album" in mapping
        assert mapping["Music/Artist/Album"] == (
            "Artist - Album (2020)",
            "Music\\Artist\\Album",
        )


class TestWaitAndOrganize:
    def test_organizes_incrementally(
        self,
        tmp_path: Path,
    ) -> None:
        """Albums organized as directories complete."""
        dl = tmp_path / "downloads"
        (dl / "Album A").mkdir(parents=True)
        (dl / "Album A" / "01.flac").write_text("a")
        (dl / "Album B").mkdir(parents=True)
        (dl / "Album B" / "01.flac").write_text("b")

        results: dict[str, Any] = {
            "Art1 - Album A (2020)": {
                "directory": "Music\\Art1\\Album A",
                "username": "u1",
                "files": [],
            },
            "Art2 - Album B (2021)": {
                "directory": "Music\\Art2\\Album B",
                "username": "u2",
                "files": [],
            },
        }

        mock_client = MagicMock()
        # Poll 1: only Album A done
        # Poll 2: both done
        # slskd returns full remote paths with backslashes
        mock_client.transfers.get_all_downloads.side_effect = [
            [
                {
                    "username": "u1",
                    "directories": [
                        {
                            "directory": ("Music\\Art1\\Album A"),
                            "files": [
                                {
                                    "filename": "01.flac",
                                    "state": ("Completed, Succeeded"),
                                },
                            ],
                        },
                    ],
                },
                {
                    "username": "u2",
                    "directories": [
                        {
                            "directory": ("Music\\Art2\\Album B"),
                            "files": [
                                {
                                    "filename": "01.flac",
                                    "state": "InProgress",
                                },
                            ],
                        },
                    ],
                },
            ],
            [
                {
                    "username": "u1",
                    "directories": [
                        {
                            "directory": ("Music\\Art1\\Album A"),
                            "files": [
                                {
                                    "filename": "01.flac",
                                    "state": ("Completed, Succeeded"),
                                },
                            ],
                        },
                    ],
                },
                {
                    "username": "u2",
                    "directories": [
                        {
                            "directory": ("Music\\Art2\\Album B"),
                            "files": [
                                {
                                    "filename": "01.flac",
                                    "state": ("Completed, Succeeded"),
                                },
                            ],
                        },
                    ],
                },
            ],
        ]

        with patch("rymparser.organizer.time.sleep"):
            moved, skipped = wait_and_organize(
                mock_client,
                results,
                {"u1", "u2"},
                dl,
                timeout=60,
                poll_interval=1,
            )

        assert moved == 2
        assert skipped == 0
        assert (dl / "Art1" / "Album A (2020)" / "01.flac").exists()
        assert (dl / "Art2" / "Album B (2021)" / "01.flac").exists()

    def test_timeout_returns_partial(
        self,
        tmp_path: Path,
    ) -> None:
        """On timeout, already-organized albums stay."""
        dl = tmp_path / "downloads"
        (dl / "Album A").mkdir(parents=True)
        (dl / "Album A" / "01.flac").write_text("a")

        results: dict[str, Any] = {
            "Art1 - Album A (2020)": {
                "directory": "Music\\Art1\\Album A",
                "username": "u1",
                "files": [],
            },
            "Art2 - Album B (2021)": {
                "directory": "Music\\Art2\\Album B",
                "username": "u2",
                "files": [],
            },
        }

        mock_client = MagicMock()
        # Album A complete, Album B never completes
        mock_client.transfers.get_all_downloads.return_value = [
            {
                "username": "u1",
                "directories": [
                    {
                        "directory": ("Music\\Art1\\Album A"),
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": ("Completed, Succeeded"),
                            },
                        ],
                    },
                ],
            },
            {
                "username": "u2",
                "directories": [
                    {
                        "directory": ("Music\\Art2\\Album B"),
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": "InProgress",
                            },
                        ],
                    },
                ],
            },
        ]

        # time.time() calls: deadline calc, while-check,
        # logger.info inside loop, while-check (exit),
        # logger.warning in else clause.
        times = [0, 0, 0, 100, 100]
        with (
            patch("rymparser.organizer.time.sleep"),
            patch(
                "rymparser.organizer.time.time",
                side_effect=times,
            ),
        ):
            moved, skipped = wait_and_organize(
                mock_client,
                results,
                {"u1", "u2"},
                dl,
                timeout=10,
                poll_interval=1,
            )

        assert moved == 1
        assert skipped == 1
        assert (dl / "Art1" / "Album A (2020)" / "01.flac").exists()

    def test_skips_null_results(
        self,
        tmp_path: Path,
    ) -> None:
        """Null results counted as skipped immediately."""
        dl = tmp_path / "downloads"
        dl.mkdir()

        results: dict[str, Any] = {
            "Artist - Album (2020)": None,
        }

        mock_client = MagicMock()

        with (
            patch("rymparser.organizer.time.sleep"),
            patch(
                "rymparser.organizer.time.time",
                side_effect=[0, 100],
            ),
        ):
            moved, skipped = wait_and_organize(
                mock_client,
                results,
                set(),
                dl,
                timeout=10,
                poll_interval=1,
            )

        assert moved == 0
        assert skipped == 1

    def test_retries_on_failed(
        self,
        tmp_path: Path,
    ) -> None:
        """On rejected download, retries with next alternative."""
        dl = tmp_path / "downloads"
        (dl / "Album A").mkdir(parents=True)
        (dl / "Album A" / "01.flac").write_text("a")

        results: dict[str, Any] = {
            "Art1 - Album A (2020)": {
                "selected": 0,
                "alternatives": [
                    {
                        "username": "u1",
                        "directory": ("Music\\Art1\\Album A"),
                        "files": [
                            {
                                "filename": ("Music\\Art1\\Album A\\01.flac"),
                            },
                        ],
                        "format": "flac",
                        "bitrate": 0,
                    },
                    {
                        "username": "u2",
                        "directory": ("Music\\Art1v2\\Album A"),
                        "files": [
                            {
                                "filename": ("Music\\Art1v2\\Album A\\01.flac"),
                            },
                        ],
                        "format": "flac",
                        "bitrate": 0,
                    },
                ],
            },
        }

        mock_client = MagicMock()
        mock_client.transfers.get_all_downloads.side_effect = [
            # Poll 1: u1 rejected
            [
                {
                    "username": "u1",
                    "directories": [
                        {
                            "directory": ("Music\\Art1\\Album A"),
                            "files": [
                                {
                                    "filename": "01.flac",
                                    "state": ("Completed, Rejected"),
                                },
                            ],
                        },
                    ],
                },
            ],
            # Poll 2: u2 succeeded
            [
                {
                    "username": "u1",
                    "directories": [
                        {
                            "directory": ("Music\\Art1\\Album A"),
                            "files": [
                                {
                                    "filename": "01.flac",
                                    "state": ("Completed, Rejected"),
                                },
                            ],
                        },
                    ],
                },
                {
                    "username": "u2",
                    "directories": [
                        {
                            "directory": ("Music\\Art1v2\\Album A"),
                            "files": [
                                {
                                    "filename": "01.flac",
                                    "state": ("Completed, Succeeded"),
                                },
                            ],
                        },
                    ],
                },
            ],
        ]

        with patch("rymparser.organizer.time.sleep"):
            moved, skipped = wait_and_organize(
                mock_client,
                results,
                {"u1"},
                dl,
                timeout=60,
                poll_interval=1,
            )

        mock_client.transfers.enqueue.assert_called_once()
        assert moved == 1

    def test_exhausts_alternatives(
        self,
        tmp_path: Path,
    ) -> None:
        """When all alternatives rejected, marks done."""
        dl = tmp_path / "downloads"
        dl.mkdir()

        results: dict[str, Any] = {
            "Art1 - Album A (2020)": {
                "selected": 0,
                "alternatives": [
                    {
                        "username": "u1",
                        "directory": ("Music\\Art1\\Album A"),
                        "files": [
                            {"filename": "01.flac"},
                        ],
                        "format": "flac",
                        "bitrate": 0,
                    },
                ],
            },
        }

        mock_client = MagicMock()
        mock_client.transfers.get_all_downloads.return_value = [
            {
                "username": "u1",
                "directories": [
                    {
                        "directory": ("Music\\Art1\\Album A"),
                        "files": [
                            {
                                "filename": "01.flac",
                                "state": ("Completed, Rejected"),
                            },
                        ],
                    },
                ],
            },
        ]

        times = [0, 0, 0, 100, 100]
        with (
            patch("rymparser.organizer.time.sleep"),
            patch(
                "rymparser.organizer.time.time",
                side_effect=times,
            ),
        ):
            moved, skipped = wait_and_organize(
                mock_client,
                results,
                {"u1"},
                dl,
                timeout=10,
                poll_interval=1,
            )

        assert moved == 0
        assert skipped == 1
