"""Parse RYM list, artist, and chart pages into text format."""

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
)
from rymscraper.chart_parser import (
    extract_chart_slug,
    parse_chart_page,
)
from rymscraper.cli import is_chart_url
from rymscraper.config import ScraperConfig
from rymscraper.models import Album, ReleaseType
from rymscraper.parser import (
    extract_slug,
    find_next_page_url,
    parse_page,
)

__all__ = [
    "DEFAULT_TYPES",
    "SECTION_CODE_TO_TYPE",
    "Album",
    "FetchError",
    "ReleaseType",
    "ScraperConfig",
    "extract_artist_slug",
    "extract_chart_slug",
    "extract_slug",
    "fetch_all_pages",
    "fetch_artist_page",
    "fetch_chart_pages",
    "find_next_page_url",
    "is_chart_url",
    "parse_artist_page",
    "parse_chart_page",
    "parse_page",
]
