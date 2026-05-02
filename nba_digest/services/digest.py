"""Digest generation service (orchestration layer)."""

import logging
from typing import Optional

from nba_digest.api.claude import ClaudeClient
from nba_digest.api.reddit import RedditClient
from nba_digest.api.espn import ESPNClient
from nba_digest.models import Digest
from nba_digest.config import Config

log = logging.getLogger(__name__)


# Season calendar (month, day) tuples
SEASON_CALENDAR = {
    "playoffs": {"start": (4, 15), "end": (6, 25)},
    "offseason": {"start": (6, 26), "end": (10, 14)},
    "regular_season": {"start": (10, 15), "end": (4, 14)},
}


class DigestService:
    """Orchestrates digest generation with API clients."""

    def __init__(self, config: Config):
        """
        Initialize service.

        Args:
            config: Configuration object
        """
        self.config = config
        self.claude = ClaudeClient.from_config(config)
        self.reddit = RedditClient()
        self.espn = ESPNClient()

    def generate(self, season_mode: Optional[str] = None) -> Digest:
        """
        Generate NBA digest.

        Args:
            season_mode: Force season mode ('playoffs', 'regular_season', 'offseason')
                        If None, auto-detects from current date

        Returns:
            Digest model with full game data and analysis
        """
        log.info("Starting digest generation (mode: %s)", season_mode or "auto")

        # Auto-detect season mode if not provided
        if not season_mode:
            season_mode = self._detect_season_mode()
            log.info("Auto-detected season mode: %s", season_mode)

        # Get season-appropriate prompt
        prompt = self._get_prompt_for_mode(season_mode)

        # Fetch Reddit posts for context
        reddit_posts = self.reddit.fetch_posts()
        if reddit_posts:
            reddit_block = (
                "Here are the current top posts from r/nba — use these to inform "
                "the headlines, narratives, and overall fan sentiment:\n\n"
                f"{reddit_posts}\n"
            )
        else:
            reddit_block = (
                "Reddit fetch was unavailable. Search for r/nba discussion "
                "to capture fan sentiment and discourse."
            )

        # Build full prompt
        full_prompt = prompt.format(reddit_block=reddit_block)

        # Generate digest via Claude (with retries)
        digest = self.claude.generate_digest(full_prompt)

        log.info("Digest generated with %d games", len(digest.games))

        return digest

    def _detect_season_mode(self) -> str:
        """Detect current NBA season mode based on date."""
        from datetime import datetime

        now = datetime.now()
        month, day = now.month, now.day

        # Check playoff dates (Apr 15 - Jun 25)
        if (4, 15) <= (month, day) <= (6, 25):
            return "playoffs"

        # Check offseason (Jun 26 - Oct 14)
        if (6, 26) <= (month, day) <= (10, 14):
            return "offseason"

        # Everything else is regular season
        return "regular_season"

    def _get_prompt_for_mode(self, mode: str) -> str:
        """Get season-appropriate prompt template."""
        # Simplified - would include full prompts for each season mode
        # Extracted from nba_digest.py

        if mode == "playoffs":
            return """Today is {date}. Generate a structured NBA playoff digest covering last night's completed games.

{reddit_block}

Search for:
1. "NBA playoff scores results standings highlights performances {iso_date}"

Then return ONLY a JSON object with:
- date, round, main_headline, sub_headline
- games (array of completed games with scores/stats)
- active_series (all first-round matchups with current standings)
- recaps (narrative descriptions of key games)
- headlines (talking points and news items)
- standout_performances (best individual performances)
- plays_of_night_url (YouTube highlights)

Return ONLY valid JSON, no explanation."""

        elif mode == "regular_season":
            return """Generate an NBA regular season digest for {date}.

{reddit_block}

Search for top games and trends.

Return JSON with same structure as playoffs digest."""

        else:  # offseason
            return """Generate an NBA offseason roundup for {date} (this is a weekly summary).

{reddit_block}

Return JSON digest with headlines about free agency, trades, and draft news."""
