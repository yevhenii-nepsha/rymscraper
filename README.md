# rymparser

Parse [RateYourMusic](https://rateyourmusic.com) list pages into
`Artist - Album (Year)` format for
[Soulseek](http://www.slsknet.org/) search.

Handles Cloudflare Turnstile anti-bot challenges using a headed
Chromium browser with stealth plugins and a persistent browser
profile.

## Installation

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run playwright install chromium
```

## Usage

```bash
# Basic — opens browser window, saves to <slug>.txt
uv run rymparser https://rateyourmusic.com/list/user/best-albums/

# Custom output file
uv run rymparser -o albums.txt https://rateyourmusic.com/list/user/best-albums/

# Headless mode (may be blocked by Cloudflare)
uv run rymparser --headless https://rateyourmusic.com/list/user/best-albums/

# Verbose logging
uv run rymparser -v https://rateyourmusic.com/list/user/best-albums/
```

## Output format

```
Radiohead - OK Computer (1997)
Björk - Homogenic (1997)
Boards of Canada - Music Has the Right to Children (1998)
```

## Development

```bash
uv run pytest          # run tests
uv run mypy src/       # type checking
uv run ruff check .    # linting
```
