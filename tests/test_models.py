"""Tests for Album model."""

import pytest

from rymparser.models import Album, ReleaseType


class TestAlbum:
    def test_str_with_year(self) -> None:
        album = Album(
            artist="Radiohead",
            title="OK Computer",
            year="1997",
        )
        assert str(album) == "Radiohead - OK Computer (1997)"

    def test_str_without_year(self) -> None:
        album = Album(
            artist="Radiohead",
            title="OK Computer",
            year="",
        )
        assert str(album) == "Radiohead - OK Computer"

    def test_frozen(self) -> None:
        """Album instances should be immutable."""
        album = Album(artist="A", title="B", year="2000")
        try:
            album.artist = "C"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass


class TestAlbumFromLine:
    def test_with_year(self) -> None:
        album = Album.from_line("Radiohead - OK Computer (1997)")
        assert album == Album(
            "Radiohead",
            "OK Computer",
            "1997",
        )

    def test_without_year(self) -> None:
        album = Album.from_line("Radiohead - OK Computer")
        assert album == Album(
            "Radiohead",
            "OK Computer",
            "",
        )

    def test_invalid_format(self) -> None:
        with pytest.raises(ValueError, match="parse"):
            Album.from_line("no dash here")


class TestReleaseType:
    def test_release_type_enum_values(self) -> None:
        assert ReleaseType.ALBUM.value == "album"
        assert ReleaseType.EP.value == "ep"
        assert ReleaseType.LIVE_ALBUM.value == "live_album"

    def test_album_release_type_default_none(self) -> None:
        album = Album(
            artist="Neurosis",
            title="Souls at Zero",
            year="1992",
        )
        assert album.release_type is None

    def test_album_with_release_type(self) -> None:
        album = Album(
            artist="Neurosis",
            title="Souls at Zero",
            year="1992",
            release_type=ReleaseType.ALBUM,
        )
        assert album.release_type == ReleaseType.ALBUM

    def test_album_str_ignores_release_type(self) -> None:
        album = Album(
            artist="Neurosis",
            title="Souls at Zero",
            year="1992",
            release_type=ReleaseType.EP,
        )
        assert str(album) == "Neurosis - Souls at Zero (1992)"
