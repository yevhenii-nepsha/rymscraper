"""Pure HTML parsing functions for RYM pages."""

from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from rymscraper.config import ScraperConfig
from rymscraper.models import Album

_DEFAULT_CONFIG = ScraperConfig()


def parse_page(
    html: str,
    config: ScraperConfig = _DEFAULT_CONFIG,
) -> list[Album]:
    """Parse a single page of RYM list HTML.

    Args:
        html: Raw HTML string from a RYM list page.
        config: Scraper configuration with CSS selectors.

    Returns:
        List of Album objects extracted from the page.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    albums: list[Album] = []

    for row in soup.select("tr"):
        artist_el = row.select_one(config.artist_selector)
        album_el = row.select_one(config.album_selector)
        year_el = row.select_one(config.year_selector)

        if not artist_el or not album_el:
            continue

        artist = artist_el.get_text(strip=True)
        title = album_el.get_text(strip=True)
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


def find_next_page_url(
    html: str,
    current_url: str,
    config: ScraperConfig = _DEFAULT_CONFIG,
) -> str | None:
    """Find the next page URL from pagination links.

    Args:
        html: Raw HTML string from a RYM list page.
        current_url: The current page URL for resolving
            relative hrefs.
        config: Scraper configuration with pagination
            selectors.

    Returns:
        Absolute URL of the next page, or None.
    """
    soup = BeautifulSoup(html, "lxml")

    for selector in config.next_page_selectors:
        next_link = soup.select_one(selector)
        if next_link and next_link.get("href"):
            href = str(next_link["href"])
            return urljoin(current_url, href)

    return None


def extract_slug(url: str) -> str:
    """Extract list slug from RYM URL for output filename.

    Args:
        url: A RateYourMusic list URL.

    Returns:
        A filesystem-safe slug string.
    """
    path = urlparse(url).path.rstrip("/")
    parts = path.split("/")
    slug = parts[-1]
    if slug.isdigit() and len(parts) > 1:
        slug = parts[-2]
    slug = re.sub(r"[^\w\-]", "_", slug)
    return slug or "rym_list"
