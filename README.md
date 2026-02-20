# rymscraper

Parse [RateYourMusic](https://rateyourmusic.com) list and artist pages into
`Artist - Album (Year)` text files.

Handles Cloudflare Turnstile challenges using a headed Chromium browser
with stealth plugins and a persistent browser profile.

## Installation

Requires Python 3.12+ and [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run playwright install chromium
```

## Usage

### List pages

```bash
# Parse a list page — saves to <slug>.txt
uv run rymscraper https://rateyourmusic.com/list/user/best-albums/

# Custom output file
uv run rymscraper -o albums.txt https://rateyourmusic.com/list/user/best-albums/
```

### Artist pages

```bash
# Parse artist discography (albums + EPs by default)
uv run rymscraper https://rateyourmusic.com/artist/radiohead

# Only albums
uv run rymscraper --types album https://rateyourmusic.com/artist/radiohead

# Albums, EPs, and singles
uv run rymscraper --types album,ep,single https://rateyourmusic.com/artist/radiohead
```

Available `--types`: album, live_album, ep, single, compilation,
music_video, appears_on, va_compilation, bootleg, video, additional.

### Common flags

```bash
--headless    # Run browser without window (may be blocked by Cloudflare)
-o FILE       # Custom output filename
-v            # Verbose (debug) logging
```

## Output format

```
Radiohead - OK Computer (1997)
Radiohead - Kid A (2000)
Radiohead - In Rainbows (2007)
```

## Development

```bash
uv run pytest          # run tests
uv run mypy src/       # type checking
uv run ruff check .    # linting
```
