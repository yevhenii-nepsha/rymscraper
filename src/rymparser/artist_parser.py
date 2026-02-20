"""Parse RYM artist pages for discography extraction."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from rymparser.models import Album, ReleaseType

SECTION_CODE_TO_TYPE: dict[str, ReleaseType] = {
    "s": ReleaseType.ALBUM,
    "l": ReleaseType.LIVE_ALBUM,
    "e": ReleaseType.EP,
    "i": ReleaseType.SINGLE,
    "c": ReleaseType.COMPILATION,
    "o": ReleaseType.MUSIC_VIDEO,
    "a": ReleaseType.APPEARS_ON,
    "v": ReleaseType.VA_COMPILATION,
    "b": ReleaseType.BOOTLEG,
    "d": ReleaseType.VIDEO,
    "x": ReleaseType.ADDITIONAL,
}

DEFAULT_TYPES: frozenset[ReleaseType] = frozenset(
    {
        ReleaseType.ALBUM,
        ReleaseType.EP,
    }
)


def parse_artist_page(
    html: str,
    types: frozenset[ReleaseType] = DEFAULT_TYPES,
) -> list[Album]:
    """Parse RYM artist page HTML into Album list.

    Args:
        html: Full HTML of artist page (after AJAX expansion).
        types: Release types to extract.

    Returns:
        List of Album objects with release_type set.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")

    artist_el = soup.select_one("h1.artist_name_hdr")
    if not artist_el:
        return []
    artist = artist_el.get_text(strip=True)

    albums: list[Album] = []
    for code, release_type in SECTION_CODE_TO_TYPE.items():
        if release_type not in types:
            continue
        section = soup.select_one(f"#disco_type_{code}")
        if not section:
            continue
        for release in section.select("div.disco_release"):
            title_el = release.select_one("a.album")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            year_el = release.select_one(
                "span[class^='disco_year']",
            )
            year_text = year_el.get_text(strip=True) if year_el else ""
            year_match = re.search(r"\d{4}", year_text)
            year = year_match.group(0) if year_match else ""
            albums.append(
                Album(
                    artist=artist,
                    title=title,
                    year=year,
                    release_type=release_type,
                ),
            )

    return albums


def extract_artist_slug(url: str) -> str:
    """Extract artist slug from RYM artist URL.

    Args:
        url: A RateYourMusic artist URL.

    Returns:
        A filesystem-safe slug string.
    """
    path = urlparse(url).path.rstrip("/")
    parts = path.split("/")
    return parts[-1] if parts else "artist"
