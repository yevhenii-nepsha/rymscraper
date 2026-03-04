"""Parse RYM chart pages into album lists."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from rymscraper.models import Album

_ITEM_SELECTOR = "div.page_charts_section_charts_item"
_TITLE_SELECTOR = (
    "a.page_charts_section_charts_item_link span.ui_name_locale_original"
)
_ARTIST_SELECTOR = (
    "div.page_charts_section_charts_item_credited_text"
    " a.artist span.ui_name_locale_original"
)
_DATE_SELECTOR = "div.page_charts_section_charts_item_date"


def parse_chart_page(html: str) -> list[Album]:
    """Parse a single RYM chart page into Album list.

    Args:
        html: Raw HTML string from a RYM chart page.

    Returns:
        List of Album objects extracted from the page.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    albums: list[Album] = []

    for item in soup.select(_ITEM_SELECTOR):
        title_el = item.select_one(_TITLE_SELECTOR)
        artist_el = item.select_one(_ARTIST_SELECTOR)
        if not title_el or not artist_el:
            continue

        title = title_el.get_text(strip=True)
        artist = artist_el.get_text(strip=True)

        date_el = item.select_one(_DATE_SELECTOR)
        date_text = date_el.get_text(strip=True) if date_el else ""
        year_match = re.search(r"\d{4}", date_text)
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


def extract_chart_slug(url: str) -> str:
    """Extract a filesystem-safe slug from chart URL.

    Args:
        url: A RateYourMusic chart URL.

    Returns:
        A slug string for output filenames.
    """
    path = urlparse(url).path.rstrip("/")
    parts = [p for p in path.split("/") if p]
    # Skip trailing page number (but not years)
    if parts and parts[-1].isdigit() and len(parts[-1]) < 4:
        parts = parts[:-1]
    # Skip "charts" prefix and "excl:ratings"
    meaningful = [p for p in parts if p not in {"charts", "excl:ratings"}]
    slug = "-".join(meaningful)
    slug = re.sub(r"[^\w\-]", "_", slug)
    return slug or "rym_chart"
