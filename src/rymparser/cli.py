"""CLI entry point for rymparser."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from rymparser.browser import FetchError, fetch_all_pages
from rymparser.config import ScraperConfig
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
            "Parse RYM list pages into 'Artist - Album (Year)' format."
        ),
    )
    parser.add_argument(
        "url",
        help="RYM list URL to parse",
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

    output_file = (
        Path(args.output)
        if args.output
        else Path(f"{extract_slug(args.url)}.txt")
    )
    config = ScraperConfig(headless=args.headless)

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
        output_file.write_text("\n".join(str(a) for a in albums) + "\n")
    except OSError as exc:
        logger.error(
            "Failed to write %s: %s",
            output_file,
            exc,
        )
        sys.exit(1)

    logger.info(
        "Done! %d albums written to %s",
        len(albums),
        output_file,
    )
