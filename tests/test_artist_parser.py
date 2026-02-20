"""Tests for artist page parser."""

import os
from pathlib import Path

import pytest

from rymscraper.artist_parser import (
    extract_artist_slug,
    parse_artist_page,
)
from rymscraper.models import ReleaseType

_NEUROSIS_HTML = "/tmp/rym_artist_neurosis.html"

ARTIST_HTML = """\
<html>
<body>
<h1 class="artist_name_hdr">Neurosis</h1>

<div id="disco_type_s">
  <div class="disco_release">
    <div class="disco_mainline">
      <a class="album" href="/release/album/neurosis/souls-at-zero/">
        Souls at Zero
      </a>
    </div>
    <div class="disco_subline">
      <span class="disco_year_y">1992</span>
    </div>
  </div>
  <div class="disco_release">
    <div class="disco_mainline">
      <a class="album"
         href="/release/album/neurosis/through-silver-in-blood/">
        Through Silver in Blood
      </a>
    </div>
    <div class="disco_subline">
      <span class="disco_year_y">1996</span>
    </div>
  </div>
</div>

<div id="disco_type_e">
  <div class="disco_release">
    <div class="disco_mainline">
      <a class="album"
         href="/release/ep/neurosis/the-word-as-law/">
        The Word as Law
      </a>
    </div>
    <div class="disco_subline">
      <span class="disco_year_y">1990</span>
    </div>
  </div>
</div>

<div id="disco_type_i">
  <div class="disco_release">
    <div class="disco_mainline">
      <a class="album"
         href="/release/single/neurosis/locust-star/">
        Locust Star
      </a>
    </div>
    <div class="disco_subline">
      <span class="disco_year_y">1996</span>
    </div>
  </div>
</div>

</body>
</html>
"""


@pytest.fixture
def artist_html() -> str:
    """Minimal RYM artist page HTML fixture."""
    return ARTIST_HTML


def test_parse_artist_page_default_types(
    artist_html: str,
) -> None:
    """Default types (album+ep) returns albums and EPs."""
    albums = parse_artist_page(artist_html)
    assert len(albums) == 3  # 2 albums + 1 EP


def test_parse_artist_page_albums_only(
    artist_html: str,
) -> None:
    albums = parse_artist_page(
        artist_html,
        types=frozenset({ReleaseType.ALBUM}),
    )
    assert len(albums) == 2
    assert all(a.release_type == ReleaseType.ALBUM for a in albums)


def test_parse_artist_page_sets_release_type(
    artist_html: str,
) -> None:
    albums = parse_artist_page(artist_html)
    types = {a.release_type for a in albums}
    assert types == {ReleaseType.ALBUM, ReleaseType.EP}


def test_parse_artist_page_extracts_artist(
    artist_html: str,
) -> None:
    albums = parse_artist_page(artist_html)
    assert all(a.artist == "Neurosis" for a in albums)


def test_parse_artist_page_extracts_year(
    artist_html: str,
) -> None:
    albums = parse_artist_page(artist_html)
    souls = [a for a in albums if a.title == "Souls at Zero"]
    assert len(souls) == 1
    assert souls[0].year == "1992"


def test_parse_artist_page_empty_html() -> None:
    assert parse_artist_page("") == []


def test_parse_artist_page_no_matching_sections(
    artist_html: str,
) -> None:
    albums = parse_artist_page(
        artist_html,
        types=frozenset({ReleaseType.BOOTLEG}),
    )
    assert albums == []


def test_extract_artist_slug() -> None:
    url = "https://rateyourmusic.com/artist/neurosis"
    assert extract_artist_slug(url) == "neurosis"


def test_extract_artist_slug_trailing_slash() -> None:
    url = "https://rateyourmusic.com/artist/neurosis/"
    assert extract_artist_slug(url) == "neurosis"


@pytest.mark.skipif(
    not os.path.exists(_NEUROSIS_HTML),
    reason="Real HTML file not available",
)
def test_parse_real_neurosis_page() -> None:
    """Smoke test with real Neurosis artist page HTML."""
    html = Path(_NEUROSIS_HTML).read_text()
    albums = parse_artist_page(html)

    # Should find albums and EPs
    assert len(albums) > 0

    # All should be Neurosis
    assert all(a.artist == "Neurosis" for a in albums)

    # All should have release_type set
    assert all(a.release_type is not None for a in albums)

    # Check type distribution
    album_count = sum(1 for a in albums if a.release_type == ReleaseType.ALBUM)
    ep_count = sum(1 for a in albums if a.release_type == ReleaseType.EP)

    # Neurosis has ~11 albums and ~5 EPs
    assert album_count >= 5
    assert ep_count >= 3
