"""Parse RYM list pages for Soulseek search."""

from rymparser.browser import FetchError, fetch_all_pages
from rymparser.config import ScraperConfig
from rymparser.models import Album
from rymparser.parser import (
    extract_slug,
    find_next_page_url,
    parse_page,
)

__all__ = [
    "Album",
    "FetchError",
    "ScraperConfig",
    "extract_slug",
    "fetch_all_pages",
    "find_next_page_url",
    "parse_page",
]
