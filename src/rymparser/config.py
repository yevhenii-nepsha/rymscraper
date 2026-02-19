"""Configuration for rymparser."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ScraperConfig:
    """All configurable values for the scraper.

    All timeout values are in seconds for consistency.
    """

    # Browser
    browser_data_dir: Path = field(
        default_factory=lambda: Path.cwd() / "browser_data"
    )
    headless: bool = False
    viewport_width: int = 1280
    viewport_height: int = 800

    # Timeouts (all in seconds)
    content_timeout: float = 90.0
    selector_poll_interval: float = 5.0
    turnstile_wait: float = 3.0
    post_turnstile_wait: float = 2.0
    page_load_wait: float = 2.0
    turnstile_click_timeout: float = 3.0

    # Retry limits
    max_turnstile_attempts: int = 3

    # CSS selectors
    content_selector: str = ".list_artist, .list_album"
    artist_selector: str = ".list_artist"
    album_selector: str = ".list_album"
    year_selector: str = ".rel_date"
    next_page_selectors: tuple[str, ...] = (
        "a.navlinknext",
        "a.ui_pagination_next",
        'a[rel="next"]',
    )
