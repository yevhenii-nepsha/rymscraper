"""CLI entry point for rymparser."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from rymparser.artist_parser import (
    DEFAULT_TYPES,
    extract_artist_slug,
)
from rymparser.browser import (
    FetchError,
    fetch_all_pages,
    fetch_artist_page,
)
from rymparser.config import ScraperConfig
from rymparser.models import ReleaseType
from rymparser.parser import extract_slug

logger = logging.getLogger(__name__)


def validate_url(url: str) -> bool:
    """Check if URL is from rateyourmusic.com.

    Args:
        url: The URL string to validate.

    Returns:
        True if the URL belongs to rateyourmusic.com.
    """
    if not url:
        return False
    parsed = urlparse(url)
    return "rateyourmusic.com" in parsed.netloc


def is_artist_url(url: str) -> bool:
    """Check if URL points to an artist page.

    Args:
        url: A RateYourMusic URL.

    Returns:
        True if the URL path starts with /artist/.
    """
    path = urlparse(url).path
    return path.startswith("/artist/")


def _parse_types(
    raw: str | None,
) -> frozenset[ReleaseType]:
    """Parse comma-separated release types string.

    Args:
        raw: Comma-separated release type values,
            or None for defaults.

    Returns:
        Frozenset of ReleaseType values.

    Raises:
        ValueError: If any type string is invalid.
    """
    if raw is None:
        return DEFAULT_TYPES
    values = {v.strip() for v in raw.split(",")}
    valid = {t.value for t in ReleaseType}
    invalid = values - valid
    if invalid:
        raise ValueError(
            f"Invalid release types: {invalid}. Valid: {sorted(valid)}"
        )
    return frozenset(ReleaseType(v) for v in values)


def parse_args(
    argv: list[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list. Uses sys.argv if None.

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Parse RYM list/artist pages into 'Artist - Album (Year)' format."
        ),
    )
    parser.add_argument(
        "url",
        help="RYM list or artist URL to parse",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename (default: from URL slug)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--types",
        default=None,
        help=(
            "Comma-separated release types for artist "
            "pages (default: album,ep). Options: "
            + ", ".join(t.value for t in ReleaseType)
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (debug) logging",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Args:
        argv: Argument list. Uses sys.argv if None.
    """
    args = parse_args(argv)

    logging.basicConfig(
        level=(logging.DEBUG if args.verbose else logging.INFO),
        format="%(levelname)s: %(message)s",
    )

    if not validate_url(args.url):
        logger.error(
            "Not a rateyourmusic.com URL: %s",
            args.url,
        )
        sys.exit(1)

    try:
        types = _parse_types(args.types)
    except ValueError as exc:
        logger.error("Invalid --types: %s", exc)
        sys.exit(1)

    config = ScraperConfig(headless=args.headless)

    if is_artist_url(args.url):
        slug = extract_artist_slug(args.url)
        output_file = Path(args.output) if args.output else Path(f"{slug}.txt")
        try:
            albums = fetch_artist_page(
                args.url,
                types=types,
                config=config,
            )
        except FetchError as exc:
            logger.error(
                "Failed to fetch artist page: %s",
                exc,
            )
            sys.exit(1)
    else:
        output_file = (
            Path(args.output)
            if args.output
            else Path(f"{extract_slug(args.url)}.txt")
        )
        try:
            albums = fetch_all_pages(
                args.url,
                config=config,
            )
        except FetchError as exc:
            logger.error(
                "Failed to fetch albums: %s",
                exc,
            )
            sys.exit(1)

    if not albums:
        logger.error("No albums found. Check debug_page.html if created.")
        sys.exit(1)

    try:
        output_file.write_text(
            "\n".join(str(a) for a in albums) + "\n",
        )
    except OSError as exc:
        logger.error(
            "Failed to write %s: %s",
            output_file,
            exc,
        )
        sys.exit(1)

    logger.info(
        "%d albums written to %s",
        len(albums),
        output_file,
    )
