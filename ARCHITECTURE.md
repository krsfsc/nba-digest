# Architecture Guide

This document explains the NBA Digest codebase structure, design decisions, and how the modules work together.

## Overview

NBA Digest is built using the **WAT framework** (Workflows, Agents, Tools) architecture:

- **Workflows**: Define the business logic (digest generation, email sending)
- **Agents**: Coordinate module interactions (DigestService, EmailService)
- **Tools**: Handle external integrations (API clients, file I/O)

## Module Responsibilities

### `models.py` — Data Structures

**Purpose**: Type-safe data models with validation

Defines Pydantic models that validate data at parse time:

- `Game` — Individual game result with score validation (scores ≥ 0, game number 1-7)
- `ActiveSeries` — Playoff series standings (valid conference, wins 0-4)
- `StandoutPerformance` — Player highlight with stats
- `Recap` — Game narrative
- `Headline` — News item
- `Digest` — Complete day's digest with full validation

**Key method**: `Digest.from_claude_response()` parses raw Claude response (with markdown fences) into validated model

**Why Pydantic?**
- Type-safe: IDE autocomplete, mypy type checking
- Validates at parse time: Fail fast if Claude returns invalid JSON
- Serializable: `.dict()` and `.json()` methods for caching

### `config.py` — Configuration

**Purpose**: Load and validate environment configuration

`Config` dataclass with `from_env()` classmethod:

- **Required**: `ANTHROPIC_API_KEY`, `GMAIL_APP_PASSWORD`
- **Optional**: sender email, recipient email, cache directory, docs directory
- **Validation**: Raises `ValueError` if required fields missing

**Design**: Single source of truth for all configuration; no hardcoded values

### `api/` — External API Clients

#### `api/claude.py` — Claude API Integration

**Purpose**: Call Claude API to generate digests

`ClaudeClient` with retry logic:

1. Try API call
2. On 429 (rate limit): Wait 180s, retry
3. On JSON parse error: Wait 90s × attempt, retry
4. After 3 attempts: Raise `RuntimeError`

**Returns**: Validated `Digest` model (not raw dict)

**Design rationale**: Retry logic prevents transient failures from cascading; exponential backoff prevents hammering rate-limited API

#### `api/reddit.py` — Reddit API

**Purpose**: Fetch top posts from r/nba

`RedditClient.fetch_posts()` returns formatted string like:

```
Top r/nba posts:
1. Post Title (100 pts · 50 comments)
2. Another Post (80 pts · 40 comments)
...
```

**Design**: Non-fatal failures return empty string; digest can proceed without Reddit context

#### `api/espn.py` — ESPN API

**Purpose**: Fetch playoff series standings

`ESPNClient.fetch_series()` returns list of active series with:
- Team names and abbreviations
- Win counts
- Team colors (for HTML styling)

**Design**: Scans up to 7 days for active matchups; useful during playoffs

### `builders/` — HTML Generation

#### `builders/email.py` — Email HTML

**Purpose**: Convert validated `Digest` to email HTML

`EmailBuilder.build(digest, iso_date)` returns complete HTML email with:
- Masthead with date and main headline
- Games section (scores, venues, series status)
- Series standings (playoff matchups)
- Recaps (game narratives)
- Headlines (news items)
- Standout performances (player stats)
- Plays of the night (YouTube highlights link)

**Design**: Takes type-safe `Digest` model; outputs HTML with escaped content (XSS protection)

**E-ink color palette**: Optimized for e-reader displays (high contrast, limited colors)

#### `builders/page.py` — Archive Pages

**Purpose**: Wrap email HTML with navigation for individual day pages

`PageBuilder.build(digest, html_body, iso_date)` adds:
- Previous/next day navigation
- Date header
- Back to index link

**Design**: Reuses email HTML; minimal wrapper adds context

#### `builders/index.py` — Index Page

**Purpose**: Build main archive landing page

`IndexBuilder.build()` generates HTML with:
- Latest digest hero section
- Playoff standings (if playoffs active)
- Archive listing grouped by month
- Fallback headlines (extracted from HTML if cache missing)

**Design**: No external API calls; reads from cache + HTML files

### `services/` — Business Logic

#### `services/digest.py` — Digest Orchestration

**Purpose**: Coordinate digest generation

`DigestService.generate(season_mode=None)`:

1. Auto-detect season mode (playoffs/regular/offseason) if not provided
2. Get season-appropriate prompt template
3. Fetch Reddit posts (for context)
4. Format dates and inject into prompt
5. Call Claude API with retry logic
6. Return validated `Digest` model

**Season modes**:
- **Playoffs** (Apr 15 - Jun 25): Full game coverage, series standings
- **Regular season** (Oct 15 - Apr 14): Top games and trends
- **Offseason** (Jun 26 - Oct 14): Weekly free agency/trade news

**Design**: Pure orchestration; delegates to API clients and returns validated model

#### `services/email.py` — Email Sending

**Purpose**: Send digest via Gmail SMTP

`EmailService.send(to_email, subject, html_body, text_body)`:

1. Connect to Gmail SMTP server
2. Create MIME multipart message (plaintext + HTML)
3. Send to recipient
4. Handle authentication and SSL errors gracefully

**Design**: Separate from building logic; reusable for any message

#### `services/storage.py` — File I/O

**Purpose**: Cache digests and save HTML files

Methods:
- `cache_digest(digest, iso_date)` → Saves `cache/digest-{iso_date}.json`
- `load_digest(iso_date)` → Loads cached digest
- `save_page(html, iso_date)` → Saves `docs/{iso_date}.html`
- `save_index(html)` → Saves `docs/index.html`

**Design**: Abstracts file paths; handles directory creation

### `cli/` — Command-Line Entry Points

#### `cli/digest.py` — Main Entry Point

**Purpose**: Daily digest generation and email sending

`main()` function:

1. Load config from environment
2. Generate digest (uses `DigestService`)
3. Build email HTML (uses `EmailBuilder`)
4. Build archive page (uses `PageBuilder`)
5. Save files (uses `StorageService`)
6. Update index (uses `IndexBuilder`)
7. Send email (uses `EmailService`)

**Usage**: `python -m nba_digest` or GitHub Actions workflow

#### `cli/rerun.py` — Re-run for Specific Date

**Purpose**: Generate digest for a past date (for backfilling)

`main()` function accepts optional date argument:

```bash
python -m nba_digest.cli.rerun 2026-04-27  # Rerun for April 27
python -m nba_digest.cli.rerun             # Rerun for yesterday
```

**Usage**: Used by `rerun-digest.yml` workflow for missed dates

## Data Flow Diagram

```
Environment Variables
    ↓
Config.from_env()
    ↓
DigestService.generate()
    ├─→ RedditClient.fetch_posts()
    └─→ ClaudeClient.generate_digest()
        ├─→ Anthropic API (Claude)
        └─→ Digest.from_claude_response()
            └─→ Pydantic validation
    ↓
EmailBuilder.build(digest)
    ↓
PageBuilder.build(digest, html)
    ↓
StorageService.cache_digest()
StorageService.save_page()
IndexBuilder.build()
StorageService.save_index()
    ↓
EmailService.send()
    ├─→ Gmail SMTP
    └─→ Email to recipient
```

## Design Principles

### 1. Separation of Concerns

Each module has a single responsibility:

- **API clients**: External integrations
- **Builders**: Presentation logic
- **Services**: Business logic
- **Models**: Data validation
- **Config**: Environment handling

### 2. Type Safety

- Full type hints throughout
- Pydantic models with validation
- mypy type checking on CI
- No `Any` types (except where necessary)

### 3. Testability

- No global state
- Dependency injection via constructor
- All external APIs mockable
- Pure functions where possible

### 4. Resilience

- Retry logic with exponential backoff
- Non-fatal failures degrade gracefully (e.g., Reddit fetch)
- Detailed logging for debugging
- Clear error messages

### 5. Maintainability

- ~2,000 lines across organized modules
- Clear naming conventions
- Comprehensive docstrings
- Documentation (this file, README, code comments)

## Adding Features

### Adding a New API Client

1. Create `nba_digest/api/newapi.py`
2. Implement client class with type hints
3. Add unit tests in `tests/test_api.py`
4. Update `DigestService` if needed
5. Document in this guide

### Adding a Builder

1. Create `nba_digest/builders/newbuilder.py`
2. Implement builder class (takes `Digest` as input, returns `str`)
3. Add unit tests in `tests/test_builders.py`
4. Update CLI to use new builder
5. Document in this guide

### Adding Type Hints

1. Use PEP 484 syntax (e.g., `def foo(x: int) -> str:`)
2. Use `Optional[T]` for nullable values
3. Use `List[T]`, `Dict[K, V]` for collections
4. Run `mypy nba_digest/ --strict` to validate
5. Fix any type errors before committing

## Testing

### Running Tests

```bash
pytest tests/ -v                    # All tests
pytest tests/test_models.py -v      # Model tests only
pytest --cov=nba_digest             # Coverage report
```

### Writing Tests

1. Use pytest fixtures in `tests/conftest.py` for common data
2. Mock external APIs (`@patch('nba_digest.api.claude.Anthropic')`)
3. Test both success and failure paths
4. Keep tests focused (one assertion per test when possible)

### Test Categories

- `test_models.py`: Pydantic validation
- `test_api.py`: API clients with mocks
- `test_builders.py`: HTML output validation
- `test_services.py`: Service integration
- `test_config.py`: Configuration handling

## Deployment

### GitHub Actions Workflow

`.github/workflows/nba-digest.yml` runs daily at 7 AM Pacific:

1. Checks out code
2. Sets up Python 3.12
3. Installs dependencies
4. Runs `python -m nba_digest`
5. Commits changes (cache/ + docs/) to repository

### Manual Trigger

Use `.github/workflows/rerun-digest.yml` to backfill missed dates:

```bash
gh workflow run rerun-digest.yml -f date=2026-04-27
```

## Troubleshooting

### "Your credit balance is too low"

The Anthropic API account has insufficient credits. Log into console.anthropic.com and purchase credits.

### "Reddit fetch failed (non-fatal)"

Reddit API is temporarily unavailable. This is OK; digest proceeds without Reddit context. Check Reddit uptime.

### JSON parse error with retries

Claude's response didn't match expected format. Check:
1. Prompt format (does it request JSON?)
2. Claude model version (should be sonnet-4-6)
3. Response length (check logs for truncation)

### Email not sending

Check Gmail app password:
1. Must be an app-specific password (not regular password)
2. Must have 16 characters with spaces
3. Account must have 2-factor authentication enabled

## Performance

Current performance (typical run):

- Reddit fetch: 200-500ms
- Claude API call: 5-15s (with retries if needed)
- HTML building: 100-200ms
- File I/O: 50-100ms
- Email sending: 1-2s

Total: 6-20 seconds per digest

## Future Improvements

- [ ] Async API calls (faster processing)
- [ ] Database caching (instead of JSON files)
- [ ] Advanced image fetching for player headshots
- [ ] More sports (NFL, NBA, MLB, etc.)
- [ ] Subscription management (multiple email addresses)
- [ ] Web dashboard for digest preview
