"""Parse RYM collection pages into album lists."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from rymscraper.models import Album

_ITEM_SELECTOR = "div.or_q_albumartist"
_ARTIST_SELECTOR = "a.artist"
_ALBUM_SELECTOR = "a.album"
_YEAR_SELECTOR = "span.smallgray"


def parse_collection_page(html: str) -> list[Album]:
    """Parse a single RYM collection page into Album list.

    Args:
        html: Raw HTML string from a RYM collection page.

    Returns:
        List of Album objects extracted from the page.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    albums: list[Album] = []

    for item in soup.select(_ITEM_SELECTOR):
        artist_el = item.select_one(_ARTIST_SELECTOR)
        title_el = item.select_one(_ALBUM_SELECTOR)
        if not artist_el or not title_el:
            continue

        artist = artist_el.get_text(strip=True)
        title = title_el.get_text(strip=True)

        year_el = item.select_one(_YEAR_SELECTOR)
        year_text = year_el.get_text(strip=True) if year_el else ""
        year_match = re.search(r"\d{4}", year_text)
        year = year_match.group(0) if year_match else ""

        if artist and title:
            albums.append(
                Album(
                    artist=artist,
                    title=title,
                    year=year,
                ),
            )

    return albums


def extract_collection_slug(url: str) -> str:
    """Extract a filesystem-safe slug from collection URL.

    Args:
        url: A RateYourMusic collection URL.

    Returns:
        A slug string for output filenames.
    """
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    # Skip "collection" prefix
    meaningful = [p for p in parts if p != "collection"]
    # Strip trailing page number (digits only, not a filter)
    if meaningful and meaningful[-1].isdigit() and len(meaningful[-1]) < 4:
        meaningful = meaningful[:-1]
    slug = "_".join(meaningful)
    slug = re.sub(r"[^\w\-]", "_", slug)
    return slug or "rym_collection"
