"""CLI entry point for rymparser with subcommands."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from urllib.parse import urlparse

from rymparser.browser import FetchError, fetch_all_pages
from rymparser.config import ScraperConfig
from rymparser.models import Album
from rymparser.parser import extract_slug
from rymparser.settings import AppSettings, load_settings

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


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with subcommands.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        description="RYM list parser + Soulseek search",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--config",
        help="Path to config.toml",
    )

    subs = parser.add_subparsers(dest="command")

    # parse
    p_parse = subs.add_parser(
        "parse",
        help="Parse RYM list to album file",
    )
    p_parse.add_argument("url", help="RYM list URL")
    p_parse.add_argument(
        "-o",
        "--output",
        help="Output filename",
    )
    p_parse.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless",
    )

    # search
    p_search = subs.add_parser(
        "search",
        help="Search albums in Soulseek",
    )
    p_search.add_argument(
        "file",
        help="Album list file (.txt)",
    )
    p_search.add_argument(
        "-o",
        "--output",
        help="Output results file",
    )
    p_search.add_argument(
        "--auto",
        action="store_true",
        help="Auto-select best result per album",
    )
    p_search.add_argument(
        "--format",
        help="Override preferred format (flac, mp3)",
    )
    p_search.add_argument(
        "--min-bitrate",
        type=int,
        help="Override minimum bitrate",
    )
    p_search.add_argument(
        "--min-files",
        type=int,
        help="Minimum audio files per result",
    )

    # download
    p_download = subs.add_parser(
        "download",
        help="Download from search results",
    )
    p_download.add_argument(
        "file",
        help="Search results file (.json)",
    )
    p_download.add_argument(
        "--downloads-dir",
        help="Path to slskd downloads directory",
    )

    # go (all-in-one)
    p_go = subs.add_parser(
        "go",
        help="Parse + search + download",
    )
    p_go.add_argument("url", help="RYM list URL")
    p_go.add_argument(
        "--headless",
        action="store_true",
        help="Run browser headless",
    )
    p_go.add_argument(
        "--auto",
        action="store_true",
        help="Auto-select best result per album",
    )

    return parser


def _cmd_parse(
    args: argparse.Namespace,
    settings: AppSettings,
) -> list[Album]:
    """Execute the parse subcommand.

    Args:
        args: Parsed CLI arguments.
        settings: Application settings.

    Returns:
        List of parsed albums.
    """
    if not validate_url(args.url):
        logger.error(
            "Not a rateyourmusic.com URL: %s",
            args.url,
        )
        sys.exit(1)

    config = ScraperConfig(
        headless=getattr(args, "headless", False),
    )
    try:
        albums = fetch_all_pages(
            args.url,
            config=config,
        )
    except FetchError as exc:
        logger.error("Failed to fetch: %s", exc)
        sys.exit(1)

    if not albums:
        logger.error("No albums found.")
        sys.exit(1)

    output_file = (
        Path(args.output)
        if getattr(
            args,
            "output",
            None,
        )
        else Path(f"{extract_slug(args.url)}.txt")
    )
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
        "%d albums written to %s",
        len(albums),
        output_file,
    )
    return albums


def _cmd_search(
    args: argparse.Namespace,
    settings: AppSettings,
) -> None:
    """Execute the search subcommand.

    Args:
        args: Parsed CLI arguments.
        settings: Application settings.
    """
    from rymparser.search import (
        build_query,
        filter_responses,
        rank_results,
    )
    from rymparser.slskd_client import (
        SlskdError,
        create_client,
        search_albums,
    )

    input_path = Path(args.file)
    if not input_path.exists():
        logger.error("File not found: %s", input_path)
        sys.exit(1)

    # Parse album list
    albums: list[Album] = []
    for line in input_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        albums.append(Album.from_line(line))

    if not albums:
        logger.error("No albums in %s", input_path)
        sys.exit(1)

    # Override settings from CLI flags
    if getattr(args, "format", None):
        settings = AppSettings(
            slskd_host=settings.slskd_host,
            slskd_api_key=settings.slskd_api_key,
            preferred_formats=[args.format],
            min_bitrate=settings.min_bitrate,
            search_timeout=settings.search_timeout,
            min_files=settings.min_files,
            download_dir=settings.download_dir,
        )
    if getattr(args, "min_bitrate", None):
        settings = AppSettings(
            slskd_host=settings.slskd_host,
            slskd_api_key=settings.slskd_api_key,
            preferred_formats=(settings.preferred_formats),
            min_bitrate=args.min_bitrate,
            search_timeout=settings.search_timeout,
            min_files=settings.min_files,
            download_dir=settings.download_dir,
        )
    if getattr(args, "min_files", None):
        settings = AppSettings(
            slskd_host=settings.slskd_host,
            slskd_api_key=settings.slskd_api_key,
            preferred_formats=(settings.preferred_formats),
            min_bitrate=settings.min_bitrate,
            search_timeout=settings.search_timeout,
            min_files=args.min_files,
            download_dir=settings.download_dir,
        )

    try:
        client = create_client(settings)
    except SlskdError as exc:
        logger.error("slskd error: %s", exc)
        sys.exit(1)

    all_results: dict[str, object] = {}
    for album in albums:
        query = build_query(album)
        logger.info("Searching: %s", query)

        try:
            responses = search_albums(
                client,
                query,
                timeout=settings.search_timeout,
            )
        except SlskdError as exc:
            logger.error(
                "Search failed for %s: %s",
                query,
                exc,
            )
            all_results[str(album)] = None
            continue

        filtered = filter_responses(
            responses,
            settings,
        )
        ranked = rank_results(filtered, settings)

        if not ranked:
            logger.warning(
                "No results for: %s",
                str(album),
            )
            all_results[str(album)] = None
            continue

        if getattr(args, "auto", False):
            best = ranked[0]
            logger.info(
                "Auto-selected: %s [%s %dkbps] from %s",
                str(album),
                best.format,
                best.bitrate,
                best.username,
            )
            all_results[str(album)] = {
                "username": best.username,
                "directory": best.directory,
                "files": best.files,
                "format": best.format,
                "bitrate": best.bitrate,
            }
        else:
            # Interactive mode: show top 5
            print(f"\n--- {album} ---")
            for idx, r in enumerate(ranked[:5]):
                slot = "free" if r.has_free_slot else f"queue:{r.queue_length}"
                speed_mb = r.upload_speed / 1_000_000
                print(
                    f"  [{idx + 1}] "
                    f"{r.format.upper()}"
                    f" {r.bitrate}kbps | "
                    f"{len(r.files)} files | "
                    f"{speed_mb:.1f} MB/s | "
                    f"{slot} | @{r.username}"
                )
            print("  [0] Skip")
            try:
                choice = input(
                    "  Choose [1]: ",
                ).strip()
            except EOFError:
                choice = "1"
            if choice == "0":
                all_results[str(album)] = None
                continue
            idx = int(choice) - 1 if choice.isdigit() else 0
            idx = max(0, min(idx, len(ranked) - 1))
            picked = ranked[idx]
            all_results[str(album)] = {
                "username": picked.username,
                "directory": picked.directory,
                "files": picked.files,
                "format": picked.format,
                "bitrate": picked.bitrate,
            }

    output_path = (
        Path(args.output)
        if getattr(args, "output", None)
        else input_path.with_suffix(".json")
    )
    output_path.write_text(json.dumps(all_results, indent=2) + "\n")
    found = sum(1 for v in all_results.values() if v)
    logger.info(
        "Search done: %d/%d found. Results: %s",
        found,
        len(all_results),
        output_path,
    )


def _cmd_download(
    args: argparse.Namespace,
    settings: AppSettings,
) -> None:
    """Execute the download subcommand.

    Args:
        args: Parsed CLI arguments.
        settings: Application settings.
    """
    from rymparser.organizer import organize_downloads
    from rymparser.slskd_client import (
        SlskdError,
        create_client,
        enqueue_download,
        wait_for_downloads,
    )

    input_path = Path(args.file)
    if not input_path.exists():
        logger.error("File not found: %s", input_path)
        sys.exit(1)

    results: dict[str, object] = json.loads(
        input_path.read_text(),
    )

    try:
        client = create_client(settings)
    except SlskdError as exc:
        logger.error("slskd error: %s", exc)
        sys.exit(1)

    queued = 0
    skipped = 0
    usernames: set[str] = set()
    for album_str, data in results.items():
        if data is None:
            skipped += 1
            continue
        assert isinstance(data, dict)
        username = str(data["username"])
        files = data["files"]
        assert isinstance(files, list)

        try:
            enqueue_download(client, username, files)
            logger.info("Queued: %s", album_str)
            queued += 1
            usernames.add(username)
        except SlskdError as exc:
            logger.error(
                "Failed to queue %s: %s",
                album_str,
                exc,
            )
            skipped += 1

    if queued == 0:
        logger.info("Nothing to download.")
        return

    logger.info(
        "Download queued: %d albums. Skipped: %d. Waiting for completion...",
        queued,
        skipped,
    )

    # Wait for all downloads to finish
    wait_for_downloads(client, usernames, timeout=1800)

    # Organize into Artist/Album structure
    downloads_dir_arg = getattr(
        args,
        "downloads_dir",
        None,
    )
    downloads_dir = (
        Path(downloads_dir_arg) if downloads_dir_arg else settings.download_dir
    )
    moved, org_skipped = organize_downloads(
        results,
        downloads_dir,
    )
    logger.info(
        "Organized: %d moved, %d skipped",
        moved,
        org_skipped,
    )


def main(argv: list[str] | None = None) -> None:
    """CLI entry point.

    Args:
        argv: Argument list. Uses sys.argv if None.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=(
            logging.DEBUG
            if getattr(
                args,
                "verbose",
                False,
            )
            else logging.INFO
        ),
        format="%(levelname)s: %(message)s",
    )

    if not getattr(args, "command", None):
        parser.print_help()
        sys.exit(1)

    config_path = Path(args.config) if getattr(args, "config", None) else None
    settings = load_settings(config_path=config_path)

    if args.command == "parse":
        _cmd_parse(args, settings)
    elif args.command == "search":
        _cmd_search(args, settings)
    elif args.command == "download":
        _cmd_download(args, settings)
    elif args.command == "go":
        # Pipeline: parse -> search -> download
        _cmd_parse(args, settings)
        # Create temp album file for search
        tmp_file = Path(f"{extract_slug(args.url)}.txt")
        # Simulate search args
        search_ns = argparse.Namespace(
            file=str(tmp_file),
            output=str(tmp_file.with_suffix(".json")),
            auto=getattr(args, "auto", False),
            format=None,
            min_bitrate=None,
        )
        _cmd_search(search_ns, settings)
        # Simulate download args
        dl_ns = argparse.Namespace(
            file=str(tmp_file.with_suffix(".json")),
        )
        _cmd_download(dl_ns, settings)
