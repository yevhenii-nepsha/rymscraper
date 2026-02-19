"""Parse RYM list pages into 'Artist - Album (Year)' format for Soulseek search."""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

BROWSER_DATA_DIR = Path(__file__).parent / "browser_data"
CONTENT_SELECTOR = ".list_artist, .list_album"


@dataclass
class Album:
    artist: str
    title: str
    year: str

    def format(self) -> str:
        if self.year:
            return f"{self.artist} - {self.title} ({self.year})"
        return f"{self.artist} - {self.title}"


def extract_slug(url: str) -> str:
    """Extract list slug from RYM URL for use as output filename."""
    path = urlparse(url).path.rstrip("/")
    # Skip trailing page number (e.g., /2/)
    parts = path.split("/")
    slug = parts[-1]
    if slug.isdigit() and len(parts) > 1:
        slug = parts[-2]
    slug = re.sub(r"[^\w\-]", "_", slug)
    return slug or "rym_list"


def parse_page(html: str) -> list[Album]:
    """Parse a single page of RYM list HTML and extract album entries."""
    soup = BeautifulSoup(html, "lxml")
    albums: list[Album] = []

    for row in soup.select("tr"):
        artist_el = row.select_one(".list_artist")
        album_el = row.select_one(".list_album")
        year_el = row.select_one(".rel_date")

        if not artist_el or not album_el:
            continue

        artist = artist_el.get_text(strip=True)
        title = album_el.get_text(strip=True)
        year_text = year_el.get_text(strip=True) if year_el else ""
        year_match = re.search(r"\d{4}", year_text)
        year = year_match.group(0) if year_match else ""

        if artist and title:
            albums.append(Album(artist=artist, title=title, year=year))

    return albums


def find_next_page_url(html: str, current_url: str) -> str | None:
    """Find the next page URL from pagination links."""
    soup = BeautifulSoup(html, "lxml")

    next_link = (
        soup.select_one("a.navlinknext")
        or soup.select_one("a.ui_pagination_next")
        or soup.select_one('a[rel="next"]')
    )

    if next_link and next_link.get("href"):
        href = str(next_link["href"])
        return urljoin(current_url, href)

    return None


def _click_turnstile(page: Page) -> None:
    """Try to find and click the Cloudflare Turnstile checkbox."""
    # Turnstile renders inside an iframe from challenges.cloudflare.com
    for frame in page.frames:
        if "challenges.cloudflare.com" in frame.url:
            try:
                frame.locator("body").click(timeout=3_000)
                return
            except Exception:
                pass

    # Fallback: click by bounding box of the turnstile container
    try:
        container = page.locator('[style*="display: grid"]').first
        box = container.bounding_box()
        if box:
            page.mouse.click(box["x"] + 30, box["y"] + box["height"] / 2)
            return
    except Exception:
        pass


def _wait_for_content(page: Page, timeout_sec: int = 90) -> bool:
    """Wait for RYM content to appear, handling Cloudflare Turnstile.

    Detects Cloudflare challenge and clicks the Turnstile checkbox.
    Returns True if content appeared, False on timeout.
    """
    deadline = time.time() + timeout_sec
    turnstile_attempts = 0
    max_turnstile_attempts = 3

    while time.time() < deadline:
        remaining_ms = int((deadline - time.time()) * 1000)
        if remaining_ms <= 0:
            break
        try:
            page.wait_for_selector(
                CONTENT_SELECTOR,
                timeout=min(5_000, remaining_ms),
            )
            return True
        except PlaywrightTimeout:
            title = page.title()
            if "just a moment" in title.lower():
                if turnstile_attempts < max_turnstile_attempts:
                    print("  Cloudflare challenge detected, clicking Turnstile...")
                    time.sleep(3)
                    _click_turnstile(page)
                    turnstile_attempts += 1
                time.sleep(2)
            else:
                # Not Cloudflare — give the page a bit more time for JS rendering
                time.sleep(2)

    return False


def fetch_all_pages(url: str, *, headless: bool = False) -> list[Album]:
    """Open URL with Playwright, handle Cloudflare, parse all pages.

    Uses a persistent browser profile so Cloudflare cookie persists across runs.
    Defaults to headed mode because Cloudflare blocks headless browsers.
    """
    all_albums: list[Album] = []

    stealth = Stealth()
    with stealth.use_sync(sync_playwright()) as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA_DIR),
            headless=headless,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            page = context.new_page()

            current_url = url
            page_num = 1

            while current_url:
                print(f"Fetching page {page_num}: {current_url}")
                page.goto(current_url, wait_until="domcontentloaded")

                if not _wait_for_content(page):
                    print(
                        "  ERROR: Timed out waiting for content. "
                        "Page may be blocked by Cloudflare."
                    )
                    debug_html = page.content()
                    Path("debug_page.html").write_text(debug_html)
                    print("  Saved page HTML to debug_page.html for inspection.")
                    break

                html = page.content()
                albums = parse_page(html)

                if not albums:
                    print(f"  No albums found on page {page_num}.")
                    if page_num == 1:
                        Path("debug_page.html").write_text(html)
                        print("  Saved page HTML to debug_page.html for inspection.")
                    break

                print(f"  Found {len(albums)} albums on page {page_num}.")
                all_albums.extend(albums)

                # Check for next page
                next_url = find_next_page_url(html, current_url)
                if next_url and next_url != current_url:
                    current_url = next_url
                    page_num += 1
                    time.sleep(2)
                else:
                    current_url = None
        finally:
            context.close()

    return all_albums


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse RYM list pages into 'Artist - Album (Year)' format.",
    )
    parser.add_argument("url", help="RYM list URL to parse")
    parser.add_argument(
        "-o",
        "--output",
        help="Output filename (default: derived from URL slug)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (often blocked by Cloudflare)",
    )
    args = parser.parse_args()

    parsed = urlparse(args.url)
    if "rateyourmusic.com" not in parsed.netloc:
        print(
            "WARNING: URL doesn't appear to be a rateyourmusic.com URL.",
            file=sys.stderr,
        )

    if args.output:
        output_file = args.output
    else:
        slug = extract_slug(args.url)
        output_file = f"{slug}.txt"

    albums = fetch_all_pages(args.url, headless=args.headless)

    if not albums:
        print("No albums found. Check debug_page.html if it was created.")
        sys.exit(1)

    with open(output_file, "w") as f:
        for album in albums:
            f.write(album.format() + "\n")

    print(f"\nDone! {len(albums)} albums written to {output_file}")


if __name__ == "__main__":
    main()
