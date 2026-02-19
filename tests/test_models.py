"""Tests for Album model."""

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
