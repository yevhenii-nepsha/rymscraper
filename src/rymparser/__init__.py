"""Parse RYM list pages for Soulseek search."""

from rymparser.browser import FetchError, fetch_all_pages
from rymparser.config import ScraperConfig
from rymparser.models import Album
from rymparser.organizer import organize_downloads
from rymparser.parser import (
    extract_slug,
    find_next_page_url,
    parse_page,
)
from rymparser.search import (
    AlbumSearchResult,
    build_query,
    filter_responses,
    rank_results,
)
from rymparser.settings import AppSettings, load_settings
from rymparser.slskd_client import SlskdError, wait_for_downloads

__all__ = [
    "Album",
    "AlbumSearchResult",
    "AppSettings",
    "FetchError",
    "ScraperConfig",
    "SlskdError",
    "build_query",
    "extract_slug",
    "fetch_all_pages",
    "filter_responses",
    "find_next_page_url",
    "load_settings",
    "organize_downloads",
    "parse_page",
    "rank_results",
    "wait_for_downloads",
]
