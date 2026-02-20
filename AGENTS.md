# AGENTS.md

## Project Overview

**rymscraper** parses RateYourMusic (RYM) list and artist pages into
`Artist - Album (Year)` text files. It uses a headed Chromium browser
with stealth plugins to bypass Cloudflare Turnstile protection.

## Tech Stack

- **Language**: Python 3.12
- **Package manager**: uv
- **Browser automation**: Playwright + playwright-stealth
- **HTML parsing**: BeautifulSoup4 + lxml
- **Linting**: ruff (line-length 80)
- **Type checking**: mypy (strict mode)
- **Testing**: pytest
- **Build system**: hatchling (src layout)

## Repository Layout

```
src/rymscraper/
  __init__.py          # Public API re-exports
  models.py            # Album (frozen dataclass) + ReleaseType (enum)
  config.py            # ScraperConfig (frozen dataclass, all settings)
  parser.py            # Pure HTML parsing for list pages
  artist_parser.py     # Pure HTML parsing for artist pages
  browser.py           # Playwright automation + Cloudflare bypass
  cli.py               # CLI entry point (argparse, no subcommands)

tests/
  fixtures/            # Static HTML files for parser tests
  test_models.py       # 10 tests
  test_parser.py       # 9 tests
  test_cli.py          # 17 tests
  test_browser.py      # 7 tests (mocked Playwright)
  test_artist_parser.py # 10 tests (1 conditionally-skipped smoke)
```

## Architecture

The codebase follows a strict layered design:

1. **Models** (`models.py`): `Album` frozen dataclass with
   `__str__` and `from_line()` classmethod. `ReleaseType` enum with
   11 values (album, ep, single, compilation, etc.).

2. **Parsers** (`parser.py`, `artist_parser.py`): Pure functions that
   accept HTML strings and return `list[Album]`. No I/O, no browser
   dependency. List parser handles paginated list pages. Artist parser
   handles discography pages with section-based filtering by release
   type.

3. **Browser** (`browser.py`): Playwright-based fetcher that launches
   a persistent Chromium context with stealth. Handles Cloudflare
   Turnstile via iframe click strategy. Calls parsers to return
   albums. Exposes `fetch_all_pages()` for lists and
   `fetch_artist_page()` for artists.

4. **CLI** (`cli.py`): Single-command argparse interface. Auto-detects
   artist vs list URL by path prefix (`/artist/`). Writes output to
   `.txt` files.

5. **Config** (`config.py`): All browser timeouts, CSS selectors, and
   retry settings are centralized in `ScraperConfig`. Parsers and
   browser functions accept config as an optional parameter with
   sensible defaults.

## Coding Conventions

- **Line length**: 80 characters max
- **Docstrings**: Google style
- **Type hints**: Required everywhere (mypy strict)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Dataclasses**: Always frozen
- **Exceptions**: Specific types only (no bare `except`)
- **Imports**: Sorted by ruff (isort rules)
- **Testing**: pytest with fixtures, no classes for test grouping

## Key Commands

```bash
# Install dependencies
uv sync && uv run playwright install chromium

# Run tests (53 tests)
uv run pytest

# Type checking
uv run mypy src/

# Linting
uv run ruff check .

# Run the tool
uv run rymscraper <url> [-o output.txt] [--headless] [--types album,ep] [-v]
```

## RYM Page Structure (Domain Knowledge)

### List Pages
- Album rows are `<tr>` elements with `.list_artist`, `.list_album`,
  `.rel_date` cells.
- Pagination uses `a.navlinknext`, `a.ui_pagination_next`, or
  `a[rel="next"]` links.

### Artist Pages
- Discography container: `div.section_artist_discography` > `div#discography`
- Category sections use type codes: `s`=Album, `l`=Live, `e`=EP,
  `i`=Single, `c`=Compilation, `o`=Music Video, `a`=Appears On,
  `v`=VA Compilation, `b`=Bootleg, `d`=Video, `x`=Additional.
- Section IDs follow the pattern `#disco_type_{code}`.
- Releases: `div.disco_release` with `a.album` for title,
  `span[class^="disco_year"]` for year.
- "Show all" buttons (`span.disco_expand_section_link`) trigger AJAX
  loads; the browser module clicks them and waits.

### Cloudflare Bypass
- RYM uses Cloudflare Turnstile. The browser module detects challenges
  by page title ("just a moment"), then clicks the Turnstile iframe
  checkbox.
- A persistent browser profile (`browser_data/`) preserves cookies to
  reduce challenge frequency.
- Headless mode is more likely to trigger challenges.

## Testing Notes

- All tests run without a browser or network access (Playwright is
  fully mocked in `test_browser.py`).
- `test_artist_parser.py` has one smoke test that requires a real HTML
  file at `/tmp/rym_artist_neurosis.html`; it is skipped when the file
  is absent.
- Test config sets `pythonpath = ["src"]` in pyproject.toml. LSP tools
  may show false-positive import errors on test files — ignore them.
- HTML fixtures in `tests/fixtures/` are minimal extracts of real RYM
  page structure.

## Common Pitfalls

- `ScraperConfig` is frozen. To override settings, create a new
  instance with `replace()` or pass kwargs to the constructor.
- `browser_data/` must be writable for the persistent Chromium profile.
  If tests or the tool fail with permission errors, check this
  directory.
- `Album.from_line()` expects the exact format `Artist - Title (Year)`.
  It uses a regex and raises `ValueError` on malformed input.
