"""Parse RYM list and artist pages into text format."""

from rymparser.artist_parser import (
    DEFAULT_TYPES,
    SECTION_CODE_TO_TYPE,
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
from rymparser.parser import (
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
    "extract_slug",
    "fetch_all_pages",
    "fetch_artist_page",
    "find_next_page_url",
    "parse_artist_page",
    "parse_page",
]
