"""ESPN API client for real-time playoff standings."""

import urllib.request
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

log = logging.getLogger(__name__)


class ESPNClient:
    """Fetches playoff standings from ESPN scoreboard API."""

    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
    USER_AGENT = "NBADigest/2.0"
    TIMEOUT = 10

    def fetch_series(self, days_back: int = 2) -> List[Dict[str, Any]]:
        """
        Fetch current playoff series standings from ESPN.

        Scans multiple days back to handle rest days and retrieve all active series.

        Args:
            days_back: Number of days to look back (default: 2)

        Returns:
            List of series dicts with standings, colors, seeds.
            Returns empty list on failure.
        """
        series_map: Dict[tuple, Dict[str, Any]] = {}

        for day_offset in range(days_back):
            target = datetime.now() - timedelta(days=day_offset)
            date_str = target.strftime("%Y%m%d")

            try:
                url = f"{self.BASE_URL}?seasontype=3&dates={date_str}"
                req = urllib.request.Request(url, headers={"User-Agent": self.USER_AGENT})

                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                    data = json.loads(resp.read().decode())

                self._extract_series(data, series_map)

            except Exception as e:
                log.debug("ESPN scoreboard fetch failed for %s: %s", date_str, e)
                continue

        result = list(series_map.values())
        log.info("Found %d playoff series", len(result))
        return result

    def _extract_series(
        self, data: Dict[str, Any], series_map: Dict[tuple, Dict[str, Any]]
    ) -> None:
        """Extract series data from ESPN scoreboard response."""
        for event in data.get("events", []):
            comp = (event.get("competitions") or [{}])[0]
            series = comp.get("series")

            if not series:
                continue

            competitors = comp.get("competitors", [])
            if len(competitors) != 2:
                continue

            team_data: Dict[str, Dict[str, Any]] = {}

            # Extract team info and series wins
            for c in competitors:
                team = c.get("team", {})
                abbr = team.get("abbreviation", "")

                if not abbr:
                    continue

                # Get series wins for this team
                wins = 0
                for sc in series.get("competitors", []):
                    if sc.get("id") == team.get("id"):
                        wins = int(sc.get("wins", 0) or 0)
                        break

                # Get team color
                raw_color = (team.get("color") or "8a8070").lstrip("#")

                # Get seed from curated rank
                seed_val = c.get("curatedRank", {}).get("current")

                team_data[abbr] = {
                    "color": "#" + raw_color,
                    "seed": seed_val if seed_val and str(seed_val) != "?" else None,
                    "wins": wins,
                }

            if len(team_data) != 2:
                continue

            # Create series key (sorted for consistency)
            abbrs = sorted(team_data.keys())
            key = tuple(abbrs)

            # Skip if we've already seen this series from a more recent game
            if key not in series_map:
                team1_abbr, team2_abbr = abbrs

                # Determine seeding and placement
                t1_seed = team_data[team1_abbr]["seed"]
                t2_seed = team_data[team2_abbr]["seed"]

                # Put higher seed first
                if (t1_seed and t2_seed and t1_seed > t2_seed) or (t1_seed and not t2_seed):
                    team1_abbr, team2_abbr = team2_abbr, team1_abbr

                top_seed = min(
                    (team_data[team1_abbr]["seed"] or 99, team_data[team2_abbr]["seed"] or 99)
                )

                series_map[key] = {
                    "team1": team1_abbr,
                    "team1_wins": team_data[team1_abbr]["wins"],
                    "team1_color": team_data[team1_abbr]["color"],
                    "team1_seed": team_data[team1_abbr]["seed"],
                    "team2": team2_abbr,
                    "team2_wins": team_data[team2_abbr]["wins"],
                    "team2_color": team_data[team2_abbr]["color"],
                    "team2_seed": team_data[team2_abbr]["seed"],
                    "top_seed": top_seed,
                    "conference": "",  # Will be filled in by caller
                }
