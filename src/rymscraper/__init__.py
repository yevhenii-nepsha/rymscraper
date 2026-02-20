"""Parse RYM list pages for Soulseek search."""

from rymscraper.artist_parser import (
    DEFAULT_TYPES,
    extract_artist_slug,
    parse_artist_page,
)
from rymscraper.browser import (
    FetchError,
    fetch_all_pages,
    fetch_artist_page,
)
from rymscraper.config import ScraperConfig
from rymscraper.models import Album, ReleaseType
from rymscraper.organizer import wait_and_organize
from rymscraper.parser import (
    extract_slug,
    find_next_page_url,
    parse_page,
)
from rymscraper.search import (
    AlbumSearchResult,
    build_query,
    filter_responses,
    rank_results,
)
from rymscraper.settings import AppSettings, load_settings
from rymscraper.slskd_client import SlskdError

__all__ = [
    "DEFAULT_TYPES",
    "Album",
    "AlbumSearchResult",
    "AppSettings",
    "FetchError",
    "ReleaseType",
    "ScraperConfig",
    "SlskdError",
    "build_query",
    "extract_artist_slug",
    "extract_slug",
    "fetch_all_pages",
    "fetch_artist_page",
    "filter_responses",
    "find_next_page_url",
    "load_settings",
    "parse_artist_page",
    "parse_page",
    "rank_results",
    "wait_and_organize",
]
