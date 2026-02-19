"""Tests for post-download file organization."""

from __future__ import annotations

from pathlib import Path

from rymparser.models import Album
from rymparser.organizer import (
    _album_target_dir,
    _organize_album,
    _source_dir_name,
    organize_downloads,
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
