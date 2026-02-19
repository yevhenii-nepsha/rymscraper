"""Tests for Album model."""

import pytest

from rymparser.models import Album


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
