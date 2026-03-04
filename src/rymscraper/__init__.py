"""Parse RYM list, artist, chart, and collection pages."""

from rymscraper.artist_parser import (
    DEFAULT_TYPES,
    SECTION_CODE_TO_TYPE,
    extract_artist_slug,
    parse_artist_page,
)
from rymscraper.browser import (
    FetchError,
    fetch_all_pages,
    fetch_artist_page,
    fetch_chart_pages,
    fetch_collection_pages,
)
from rymscraper.chart_parser import (
    extract_chart_slug,
    parse_chart_page,
)
from rymscraper.cli import is_chart_url, is_collection_url
from rymscraper.collection_parser import (
    extract_collection_slug,
    parse_collection_page,
)
from rymscraper.config import ScraperConfig
from rymscraper.models import Album, ReleaseType
from rymscraper.parser import (
    extract_slug,
    find_next_page_url,
    parse_page,
)
from rymscraper.spotify import sync_albums_to_spotify

__all__ = [
    "DEFAULT_TYPES",
    "SECTION_CODE_TO_TYPE",
    "Album",
    "FetchError",
    "ReleaseType",
    "ScraperConfig",
    "extract_artist_slug",
    "extract_chart_slug",
    "extract_collection_slug",
    "extract_slug",
    "fetch_all_pages",
    "fetch_artist_page",
    "fetch_chart_pages",
    "fetch_collection_pages",
    "find_next_page_url",
    "is_chart_url",
    "is_collection_url",
    "parse_artist_page",
    "parse_chart_page",
    "parse_collection_page",
    "parse_page",
    "sync_albums_to_spotify",
]
