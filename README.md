# NBA Digest

A nightly NBA playoff digest delivered to your inbox — no social media required.

Uses Claude API + web search to synthesize scores, recaps, headlines, standout performances, and r/nba discourse into a clean, e-ink styled email.

## How it works

- **Playoffs**: Nightly digest with full game coverage, series tracking, narrative recaps, and player headshots
- **Regular season**: Nightly digest with top games and standout performances
- **Offseason**: Weekly roundup (Mondays) with trades, free agency, and draft news

## Setup

1. Add repository secrets in **Settings → Secrets → Actions**:
   - `ANTHROPIC_API_KEY` — your Anthropic API key
   - `GMAIL_APP_PASSWORD` — Gmail app password ([create one here](https://myaccount.google.com/apppasswords))

2. The workflow runs automatically at 7:00 AM Pacific daily

3. You can also trigger it manually from the **Actions** tab

## Running locally

```bash
pip install anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
python nba_digest.py
```

## Architecture

### Modular Structure

The codebase has been refactored into a clean, type-safe, modular package:

```
nba_digest/
├── models.py              # Pydantic models (Game, Digest, etc.)
├── config.py              # Configuration management
├── api/                   # External API clients
│   ├── reddit.py          # Reddit API client
│   ├── claude.py          # Claude API client with retry logic
│   └── espn.py            # ESPN API client
├── builders/              # HTML generation
│   ├── email.py           # Email HTML builder
│   ├── page.py            # Archive page builder
│   └── index.py           # Index HTML builder
├── services/              # Business logic orchestration
│   ├── digest.py          # Digest generation service
│   ├── email.py           # Email sending service
│   └── storage.py         # File I/O service
└── cli/                   # Command-line entry points
    ├── digest.py          # Main digest generation
    └── rerun.py           # Re-run for specific dates
```

### Key Features

- **Type-safe**: Full type hints with Pydantic v2 models
- **Tested**: Comprehensive unit tests with mocked APIs
- **Resilient**: Retry logic (3 attempts) with exponential backoff
- **Stateless**: No global state, easy to test and reuse
- **Modular**: Clean separation of concerns (API, business logic, presentation)
- **Season-aware**: Auto-detects playoffs vs regular season vs offseason

### Data Flow

1. **Config** → Load from environment variables with validation
2. **Reddit API** → Fetch top posts from r/nba (non-fatal if unavailable)
3. **Claude API** → Generate structured digest from prompt + Reddit context
4. **Validation** → Pydantic models validate Claude's response
5. **Builders** → Convert validated digest to HTML (email + archive pages)
6. **Storage** → Cache JSON, save HTML pages, update index
7. **Email** → Send via Gmail SMTP to subscriber

### Retry Logic

- **Rate limit (429)**: Wait 180s and retry
- **JSON parse errors**: Wait 90s × attempt number and retry
- **Other errors**: Fail after 3 attempts with exponential backoff
