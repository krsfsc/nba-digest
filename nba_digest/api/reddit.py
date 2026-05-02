"""Reddit API client for fetching r/nba posts."""

import urllib.request
import json
import logging
from typing import List

log = logging.getLogger(__name__)


class RedditClient:
    """Fetches posts from r/nba subreddit."""

    BASE_URL = "https://www.reddit.com/r/nba/hot.json"
    USER_AGENT = "NBADigest/2.0"
    TIMEOUT = 15

    def fetch_posts(self, limit: int = 25) -> str:
        """
        Fetch top posts from r/nba.

        Args:
            limit: Number of posts to fetch (default: 25)

        Returns:
            Formatted string with post titles, scores, and comments.
            Returns empty string on failure (non-fatal).
        """
        url = f"{self.BASE_URL}?limit={limit}"
        headers = {"User-Agent": self.USER_AGENT}

        try:
            log.info("Fetching r/nba posts...")
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                data = json.loads(resp.read().decode())

            posts = self._parse_posts(data, limit)
            log.info("Fetched %d r/nba posts", len(posts))
            return "\n".join(posts)

        except Exception as e:
            log.warning("Reddit fetch failed (non-fatal): %s", e)
            return ""

    def _parse_posts(self, data: dict, limit: int) -> List[str]:
        """Parse Reddit JSON response into formatted post strings."""
        posts = []

        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})

            # Skip stickied posts (announcements, etc)
            if p.get("stickied"):
                continue

            flair = p.get("link_flair_text", "") or ""
            title = p.get("title", "")
            score = p.get("score", 0)
            comments = p.get("num_comments", 0)
            selftext = (p.get("selftext", "") or "")[:200]

            post_str = f"[{flair}] {title} ({score} pts, {comments} comments)"
            if selftext:
                post_str += f"\n  {selftext}"

            posts.append(post_str)

            if len(posts) >= limit:
                break

        return posts
