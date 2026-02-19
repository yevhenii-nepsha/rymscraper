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
# Parse RYM list to text file
uv run rymparser parse https://rateyourmusic.com/list/user/best-albums/

# Custom output file
uv run rymparser parse -o albums.txt https://rateyourmusic.com/list/user/best-albums/

# Headless mode (may be blocked by Cloudflare)
uv run rymparser parse --headless https://rateyourmusic.com/list/user/best-albums/

# Verbose logging
uv run rymparser -v parse https://rateyourmusic.com/list/user/best-albums/
```

## Output format

```
Radiohead - OK Computer (1997)
Björk - Homogenic (1997)
Boards of Canada - Music Has the Right to Children (1998)
```

## Soulseek Integration

rymparser can search and download albums from
the Soulseek network via [slskd](https://github.com/slskd/slskd).

### Quick Start (Docker)

1. Copy `.env.example` to `.env` and fill in your
   Soulseek credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. Start slskd:
   ```bash
   docker compose up -d slskd
   ```

3. Parse a RYM list and search Soulseek:
   ```bash
   docker compose run rymparser go \
     https://rateyourmusic.com/list/user/best-albums/ \
     --auto
   ```

### Subcommands

```bash
# Parse RYM list to text file
rymparser parse https://rateyourmusic.com/list/user/test/

# Search albums in Soulseek (interactive)
rymparser search albums.txt

# Search with auto-select
rymparser search --auto albums.txt

# Download from search results
rymparser download results.json

# All-in-one pipeline
rymparser go https://rateyourmusic.com/list/user/test/
```

### Configuration

Create `~/.config/rymparser/config.toml`:

```toml
[slskd]
host = "http://localhost:5030"
api_key = "your-api-key"

[search]
preferred_formats = ["flac", "mp3"]
min_bitrate = 320
search_timeout = 30

[download]
output_dir = "~/Music"
```

Or use environment variables: `SLSKD_HOST`,
`SLSKD_API_KEY`.

## Development

```bash
uv run pytest          # run tests
uv run mypy src/       # type checking
uv run ruff check .    # linting
```
