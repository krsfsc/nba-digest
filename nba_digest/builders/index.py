"""Archive index builder for main page."""

import logging
from pathlib import Path
from typing import Dict, List, Optional
import json
import re

log = logging.getLogger(__name__)


class IndexBuilder:
    """Builds the main archive index page."""

    def __init__(self, cache_dir: Path, docs_dir: Path):
        """
        Initialize builder.

        Args:
            cache_dir: Directory containing cached digest JSON files
            docs_dir: Directory containing generated HTML pages
        """
        self.cache_dir = Path(cache_dir)
        self.docs_dir = Path(docs_dir)

    def build(self) -> str:
        """
        Build the main index.html archive page.

        Returns:
            Complete index page HTML

        Notes:
            Extracts from nba_digest.py build_index_html() function.
            Should include:
            - Playoff picture standings (East/West columns with pip dots)
            - Hero section with latest digest
            - Tonight's games (if applicable)
            - Archive grouped by month
        """
        # Collect all digest pages
        entries = self._collect_entries()

        # Build sections
        standings_html = self._build_standings(entries)
        hero_html = self._build_hero(entries)
        tonight_html = ""  # Would be populated if applicable
        archive_html = self._build_archive(entries)

        css = """<style>
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body {
    width: 100%;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    background-color: #e8e3db;
    color: #1a1a1a;
    line-height: 1.6;
}

h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 1em 0 0.5em 0;
}

h2 {
    font-size: 1.8rem;
    font-weight: 600;
    margin: 1em 0 0.5em 0;
    color: #1a1a1a;
}

h3 {
    font-size: 1.3rem;
    font-weight: 600;
    margin: 0.75em 0 0.5em 0;
    color: #555;
}

p {
    margin: 0.75em 0;
    font-size: 1rem;
}

a {
    color: #0066cc;
    text-decoration: none;
    font-weight: 500;
}

a:hover {
    text-decoration: underline;
    color: #0052a3;
}

div {
    max-width: 900px;
    margin: 0 auto;
}
</style>"""

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NBA Digest Archive</title>
    {css}
</head>
<body>
    <div>
        {standings_html}
        {hero_html}
        {tonight_html}
        {archive_html}
    </div>
</body>
</html>"""

    def _collect_entries(self) -> List[tuple]:
        """Collect all digest entries with metadata."""
        entries = []

        for html_file in sorted(self.docs_dir.glob("????-??-??.html"), reverse=True):
            iso_date = html_file.stem
            json_file = self.cache_dir / f"digest-{iso_date}.json"

            headline = ""
            round_label = ""

            # Try to load from JSON cache
            if json_file.exists():
                try:
                    data = json.loads(json_file.read_text())
                    headline = data.get("main_headline", "")
                    round_label = data.get("round", "")
                except Exception:
                    pass

            # Fallback: extract from HTML
            if not headline:
                try:
                    html_text = html_file.read_text()
                    m = re.search(r"<h2[^>]*>([^<]+)</h2>", html_text)
                    if m:
                        headline = m.group(1).strip()
                except Exception:
                    pass

            month_key = iso_date[:7]
            entries.append((month_key, iso_date, headline, round_label))

        return entries

    def _build_standings(self, entries: List[tuple]) -> str:
        """Build playoff standings section."""
        # Would use fetch_playoff_series() to build East/West bracket display
        return ""

    def _build_hero(self, entries: List[tuple]) -> str:
        """Build hero section with latest digest."""
        if not entries:
            return ""

        month_key, iso_date, headline, round_label = entries[0]

        return f"""<div style="padding:32px;">
            <h2>{headline or "NBA Digest"}</h2>
            <p><a href="{iso_date}.html">Read full digest →</a></p>
        </div>"""

    def _build_archive(self, entries: List[tuple]) -> str:
        """Build archive listing grouped by month."""
        if not entries:
            return ""

        from itertools import groupby

        archive_html = ""

        for month_key, group in groupby(entries, key=lambda x: x[0]):
            month_str = month_key.replace("-", "–")  # e.g., "2026–04"
            archive_html += f"""<div style="padding:20px;">
                <h3>{month_str}</h3>"""

            for _, iso_date, headline, round_label in group:
                archive_html += f"""<p><a href="{iso_date}.html">{iso_date} — {headline or 'NBA Digest'}</a></p>"""

            archive_html += "</div>"

        return f"""<div style="padding:32px;"><h2>Archive</h2>{archive_html}</div>"""
