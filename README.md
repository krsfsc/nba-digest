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

- `nba_digest.py` — main script (Reddit fetch → Claude API → HTML email → Gmail)
- `.github/workflows/nba-digest.yml` — GitHub Actions cron schedule
- Retry logic (3 attempts with backoff) for API reliability
- Disk caching of each digest as JSON
- Season-aware: auto-detects playoffs vs regular season vs offseason
