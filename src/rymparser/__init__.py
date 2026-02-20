"""Parse RYM list pages for Soulseek search."""

from rymparser.artist_parser import (
    DEFAULT_TYPES,
    extract_artist_slug,
    parse_artist_page,
)
from rymparser.browser import (
    FetchError,
    fetch_all_pages,
    fetch_artist_page,
)
from rymparser.config import ScraperConfig
from rymparser.models import Album, ReleaseType
from rymparser.organizer import wait_and_organize
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
from rymparser.slskd_client import SlskdError

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
