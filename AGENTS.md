# AGENTS.md

## Project Overview

**rymscraper** parses RateYourMusic (RYM) list and artist pages into
`Artist - Album (Year)` text files, then searches and downloads those
albums from Soulseek P2P via the slskd daemon.

Full pipeline: **parse** (RYM -> album list) -> **search** (Soulseek
via slskd) -> **download** (enqueue + organize into Artist/Album
folders).

## Tech Stack

- **Language**: Python 3.12
- **Package manager**: uv
- **Browser automation**: Playwright + playwright-stealth
- **HTML parsing**: BeautifulSoup4 + lxml
- **Soulseek integration**: slskd-api (REST client for slskd daemon)
- **Linting**: ruff (line-length 80)
- **Type checking**: mypy (strict mode)
- **Testing**: pytest
- **Build system**: hatchling (src layout)
- **Containerization**: Docker + docker-compose (slskd + rymscraper)

## Repository Layout

```
src/rymscraper/
  __init__.py          # Public API re-exports (22 symbols)
  models.py            # Album (frozen dataclass) + ReleaseType (enum)
  config.py            # ScraperConfig (frozen dataclass, browser settings)
  settings.py          # AppSettings (frozen dataclass, slskd/search/download)
  parser.py            # Pure HTML parsing for list pages
  artist_parser.py     # Pure HTML parsing for artist pages
  browser.py           # Playwright automation + Cloudflare bypass
  search.py            # Soulseek search filtering & ranking
  slskd_client.py      # slskd REST API wrapper
  organizer.py         # Post-download file organization + retry
  cli.py               # CLI entry point (argparse, 4 subcommands)

tests/
  fixtures/            # Static HTML files for parser tests
  test_models.py       # 10 tests
  test_parser.py       # 9 tests
  test_cli.py          # 25 tests
  test_browser.py      # 7 tests (mocked Playwright)
  test_artist_parser.py # 10 tests (1 conditionally-skipped smoke)
  test_settings.py     # 6 tests
  test_slskd_client.py # 12 tests
  test_search.py       # 16 tests
  test_organizer.py    # 23 tests

Dockerfile             # Python 3.12 + Playwright + Chromium
docker-compose.yml     # slskd + rymscraper services
.env.example           # Required credentials template
```

## Architecture

The codebase follows a strict layered design:

### Layer 1: Models

- `models.py`: `Album` frozen dataclass with `__str__` (formats as
  `Artist - Title (Year)`) and `from_line()` classmethod (parses back).
  `ReleaseType` enum with 11 values.

### Layer 2: Parsers (pure functions, no I/O)

- `parser.py`: `parse_page()` extracts albums from list page HTML.
  `find_next_page_url()` resolves pagination links.
- `artist_parser.py`: `parse_artist_page()` extracts albums from
  artist discography HTML, filtered by release type.

### Layer 3: Browser (I/O, Playwright)

- `browser.py`: Persistent Chromium context with stealth. Handles
  Cloudflare Turnstile. `fetch_all_pages()` for lists (paginated),
  `fetch_artist_page()` for artists (expands sections).

### Layer 4: Search & Download (slskd integration)

- `slskd_client.py`: Thin wrapper around slskd REST API. Handles
  search polling, download enqueuing, transfer monitoring.
- `search.py`: `filter_responses()` filters by format, bitrate,
  file count, and album-title relevance. `rank_results()` sorts by
  format preference, free slot, bitrate, speed, queue length.
- `organizer.py`: `wait_and_organize()` polls transfers, moves
  completed albums into `Artist/Title (Year)/` structure, retries
  from alternative users on failure.

### Layer 5: Configuration

- `config.py`: `ScraperConfig` — browser timeouts, CSS selectors,
  retry settings. Used by parsers and browser.
- `settings.py`: `AppSettings` — slskd host/key, format preferences,
  bitrate, search timeout, download directory. Loaded from
  `~/.config/rymscraper/config.toml` with env var overrides.

### Layer 6: CLI

- `cli.py`: Four subcommands (`parse`, `search`, `download`, `go`).
  `go` runs the full pipeline. Auto-detects artist vs list URL.

## Coding Conventions

- **Line length**: 80 characters max
- **Docstrings**: Google style
- **Type hints**: Required everywhere (mypy strict)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Dataclasses**: Always frozen
- **Exceptions**: Specific types only (no bare `except`)
- **Imports**: Sorted by ruff (isort rules)
- **Testing**: pytest with fixtures, no classes for test grouping
  (except in Soulseek test files which use classes)

## Key Commands

```bash
# Install dependencies
uv sync && uv run playwright install chromium

# Run tests (118 tests)
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check .

# CLI subcommands
uv run rymscraper parse <url> [-o file] [--headless] [--types album,ep]
uv run rymscraper search <file.txt> [-o results.json] [--auto]
uv run rymscraper download <results.json> [--downloads-dir path]
uv run rymscraper go <url> [--headless] [--auto] [--types album,ep]
```

## CLI Subcommands

### `parse` — Scrape RYM page to album list
Fetches an RYM list or artist page, writes `Artist - Album (Year)`
lines to a `.txt` file.

### `search` — Find albums on Soulseek
Reads an album `.txt` file, searches slskd for each album, stores
top-3 alternatives per album in a `.json` file. `--auto` skips
interactive selection.

### `download` — Download and organize
Reads a search results `.json`, enqueues downloads via slskd, polls
until transfers complete, moves files into `Artist/Album (Year)/`
directory structure. Retries from alternative users on rejection.

### `go` — Full pipeline
Runs parse -> search -> download in sequence.

## Search Results JSON Format

```json
{
  "Artist - Title (Year)": {
    "selected": 0,
    "alternatives": [
      {
        "username": "peer_name",
        "directory": "@@user\\Music\\Album",
        "files": [{"filename": "01.flac", ...}],
        "format": "flac",
        "bitrate": 1411
      }
    ]
  }
}
```

## Configuration

### `~/.config/rymscraper/config.toml`

```toml
[slskd]
host = "http://localhost:5030"
api_key = "your-api-key"

[search]
preferred_formats = ["flac", "mp3"]
min_bitrate = 320
search_timeout = 30
min_files = 1

[download]
output_dir = "/absolute/path/to/downloads"
```

Priority: env vars > config.toml > defaults.
Env vars: `SLSKD_HOST`, `SLSKD_API_KEY`.

### `.env` (for Docker)

```env
SLSK_USERNAME=your_soulseek_username
SLSK_PASSWORD=your_soulseek_password
SLSKD_API_KEY=change-me-to-a-long-random-string
```

## Docker Setup

`docker-compose.yml` runs two services:
- **slskd**: Soulseek daemon (ports 5030 web, 50300 protocol).
  Volumes: `./slskd-data`, `./downloads`, `./shared`.
- **rymscraper**: The app container. Connects to slskd internally.
  Volumes: `./downloads`, `./output`.

## RYM Page Structure (Domain Knowledge)

### List Pages
- Album rows are `<tr>` with `.list_artist`, `.list_album`, `.rel_date`.
- Pagination: `a.navlinknext`, `a.ui_pagination_next`, `a[rel="next"]`.

### Artist Pages
- Discography: `div.section_artist_discography` > `div#discography`.
- Section type codes: `s`=Album, `l`=Live, `e`=EP, `i`=Single,
  `c`=Compilation, `o`=Music Video, `a`=Appears On, `v`=VA Compilation,
  `b`=Bootleg, `d`=Video, `x`=Additional.
- Section IDs: `#disco_type_{code}`.
- Releases: `div.disco_release` > `a.album` + `span[class^="disco_year"]`.
- "Show all" buttons (`span.disco_expand_section_link`) trigger AJAX.

### Cloudflare Bypass
- Detects Turnstile by page title ("just a moment").
- Clicks iframe checkbox via two strategies (iframe body, bounding box).
- Persistent profile (`browser_data/`) preserves cookies.

## slskd API Quirks

- `extension` field is often empty — `_file_ext()` falls back to
  parsing `filename`.
- `search_responses()` returns empty list while search is InProgress —
  the client polls until responses stabilize (5 rounds).
- Downloads save using only the last path component of the remote path.
- Transfer paths use backslashes; search results use forward slashes.
  The organizer normalizes both.
- Completed states: `"Completed, Succeeded"`, `"Completed, Cancelled"`,
  `"Completed, TimedOut"`, `"Completed, Errored"`,
  `"Completed, Rejected"`.
- Success state: only `"Completed, Succeeded"`.

## Testing Notes

- All 118 tests run without a browser, network, or slskd daemon
  (everything is mocked).
- `test_artist_parser.py` has one smoke test requiring
  `/tmp/rym_artist_neurosis.html`; skipped when absent.
- `pythonpath = ["src"]` in pyproject.toml. LSP tools may show
  false-positive import errors on test files — ignore them.
- HTML fixtures in `tests/fixtures/` are minimal RYM page extracts.

## Common Pitfalls

- `download_dir` in `AppSettings` defaults to `Path("downloads")`
  (relative). For the organizer to find slskd's download files,
  set an absolute path in config.toml:
  `output_dir = "/absolute/path/to/downloads"`.
- `ScraperConfig` and `AppSettings` are both frozen. Use `replace()`
  or pass kwargs to override.
- `browser_data/` must be writable for the persistent Chromium profile.
- `Album.from_line()` expects exact format `Artist - Title (Year)`.
  Raises `ValueError` on malformed input.
- The `_matches_album()` filter in `search.py` skips short words
  (<=2 chars) and stop words. Searching for albums with very short
  or common-word-only titles may over-match.
