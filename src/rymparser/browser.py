"""Browser automation for scraping RYM with Cloudflare bypass."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright_stealth import Stealth

from rymparser.config import ScraperConfig
from rymparser.parser import find_next_page_url, parse_page

if TYPE_CHECKING:
    from rymparser.models import Album

logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Raised when page fetching fails irrecoverably."""


def is_cloudflare_challenge(title: str) -> bool:
    """Check if page title indicates a Cloudflare challenge.

    Args:
        title: The page title string.

    Returns:
        True if the title matches a Cloudflare challenge.
    """
    return "just a moment" in title.lower()


def _click_turnstile(
    page: Page,
    config: ScraperConfig,
) -> bool:
    """Try to click the Cloudflare Turnstile checkbox.

    Args:
        page: The Playwright page object.
        config: Scraper configuration with timeouts.

    Returns:
        True if a click was attempted, False otherwise.
    """
    timeout_ms = int(config.turnstile_click_timeout * 1000)
    for frame in page.frames:
        if "challenges.cloudflare.com" in frame.url:
            try:
                frame.locator("body").click(timeout=timeout_ms)
                logger.debug("Clicked Turnstile iframe checkbox")
                return True
            except PlaywrightTimeout:
                logger.debug(
                    "Turnstile iframe click timed out",
                    exc_info=True,
                )

    try:
        container = page.locator('[style*="display: grid"]').first
        box = container.bounding_box()
        if box:
            page.mouse.click(
                box["x"] + 30,
                box["y"] + box["height"] / 2,
            )
            logger.debug("Clicked Turnstile via bounding box")
            return True
    except PlaywrightTimeout:
        logger.debug(
            "Turnstile bounding box fallback failed",
            exc_info=True,
        )

    logger.warning("Could not find Turnstile checkbox to click")
    return False


def _wait_for_content(
    page: Page,
    config: ScraperConfig,
) -> bool:
    """Wait for RYM content, handling Cloudflare Turnstile.

    Args:
        page: The Playwright page object.
        config: Scraper configuration with timeouts.

    Returns:
        True if content appeared, False on timeout.
    """
    deadline = time.time() + config.content_timeout
    turnstile_attempts = 0
    poll_ms = int(config.selector_poll_interval * 1000)

    while time.time() < deadline:
        remaining_ms = int((deadline - time.time()) * 1000)
        if remaining_ms <= 0:
            break

        try:
            page.wait_for_selector(
                config.content_selector,
                timeout=min(poll_ms, remaining_ms),
            )
            return True
        except PlaywrightTimeout:
            title = page.title()
            if is_cloudflare_challenge(title):
                if turnstile_attempts < (config.max_turnstile_attempts):
                    logger.info(
                        "Cloudflare challenge detected (attempt %d/%d)",
                        turnstile_attempts + 1,
                        config.max_turnstile_attempts,
                    )
                    time.sleep(config.turnstile_wait)
                    _click_turnstile(page, config)
                    turnstile_attempts += 1
                else:
                    logger.warning(
                        "Exhausted %d Turnstile attempts",
                        config.max_turnstile_attempts,
                    )
                time.sleep(config.post_turnstile_wait)
            else:
                logger.debug(
                    "Content not ready, title: %s",
                    title,
                )
                time.sleep(config.post_turnstile_wait)

    return False


def _save_debug_html(
    page: Page,
    output_dir: Path,
) -> Path:
    """Save current page HTML for debugging.

    Args:
        page: The Playwright page object.
        output_dir: Directory to save the debug file.

    Returns:
        Path to the saved debug HTML file.
    """
    debug_path = output_dir / "debug_page.html"
    debug_path.write_text(page.content())
    logger.info("Saved debug HTML to %s", debug_path)
    return debug_path


def fetch_all_pages(
    url: str,
    config: ScraperConfig | None = None,
) -> list[Album]:
    """Scrape all pages of a RYM list.

    Opens URL with Playwright, handles Cloudflare, parses
    all paginated pages. Uses a persistent browser profile
    so Cloudflare cookies survive across runs.

    Args:
        url: The RYM list URL to scrape.
        config: Scraper configuration. Uses defaults
            if None.

    Returns:
        List of Album objects from all pages.

    Raises:
        FetchError: If content cannot be loaded.
    """
    if config is None:
        config = ScraperConfig()

    all_albums: list[Album] = []
    output_dir = Path.cwd()

    stealth = Stealth()
    with stealth.use_sync(sync_playwright()) as pw:
        logger.info(
            "Launching browser (headless=%s)",
            config.headless,
        )
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(config.browser_data_dir),
            headless=config.headless,
            viewport={
                "width": config.viewport_width,
                "height": config.viewport_height,
            },
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            page = context.new_page()
            current_url: str | None = url
            page_num = 1

            while current_url:
                logger.info(
                    "Fetching page %d: %s",
                    page_num,
                    current_url,
                )
                try:
                    page.goto(
                        current_url,
                        wait_until="domcontentloaded",
                    )
                except PlaywrightTimeout as exc:
                    raise FetchError(
                        f"Navigation to {current_url} timed out: {exc}"
                    ) from exc

                if not _wait_for_content(page, config):
                    _save_debug_html(page, output_dir)
                    raise FetchError(
                        "Timed out waiting for content"
                        f" on page {page_num}. May be"
                        " blocked by Cloudflare."
                    )

                html = page.content()
                albums = parse_page(html, config)

                if not albums:
                    logger.warning(
                        "No albums on page %d",
                        page_num,
                    )
                    if page_num == 1:
                        _save_debug_html(page, output_dir)
                    break

                logger.info(
                    "Found %d albums on page %d",
                    len(albums),
                    page_num,
                )
                all_albums.extend(albums)

                next_url = find_next_page_url(
                    html,
                    current_url,
                    config,
                )
                if next_url and next_url != current_url:
                    current_url = next_url
                    page_num += 1
                    time.sleep(config.page_load_wait)
                else:
                    current_url = None
        finally:
            context.close()

    return all_albums
