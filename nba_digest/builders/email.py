"""Email HTML builder for digest generation."""

import logging
from typing import Dict, List, Any, Optional
from html import escape

from nba_digest.models import Digest

log = logging.getLogger(__name__)

# E-ink color palette
INK = {
    "bg": "#f5f0e8",
    "surface": "#ece7dc",
    "border": "#d4cdbf",
    "text": "#2c2418",
    "textMid": "#4a3f32",
    "textMuted": "#6b5e4e",
    "textFaint": "#8a8070",
    "textGhost": "#a89e8e",
}


class EmailBuilder:
    """Builds HTML emails from Digest models."""

    def __init__(self, colors: Optional[Dict[str, str]] = None):
        """
        Initialize builder.

        Args:
            colors: Custom color palette (defaults to e-ink palette)
        """
        self.colors = colors or INK

    def build(
        self, digest: Digest, iso_date: str = "", tonight: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Build complete HTML email from digest.

        Args:
            digest: Validated Digest model
            iso_date: Date in YYYY-MM-DD format (optional)
            tonight: List of tonight's upcoming games (optional)

        Returns:
            Complete HTML email as string
        """
        # This is a simplified example. The full builder would include:
        # - Masthead with title/date
        # - Main headline and sub-headline
        # - Game results table
        # - Active series standings (East/West columns)
        # - Game recaps
        # - Headlines & narratives
        # - Standout performances with player headshots
        # - Plays of the Night link
        # - Tonight's games section
        # - Footer

        # Extract from current nba_digest.py build_email_html() function
        # and refactor inline HTML into this method with type-safe inputs

        masthead = self._build_masthead(digest)
        headline_section = self._build_headline(digest)
        games_section = self._build_games(digest)
        series_section = self._build_series(digest)
        recaps_section = self._build_recaps(digest)
        headlines_section = self._build_headlines(digest)
        performances_section = self._build_performances(digest)
        tonight_section = self._build_tonight(tonight) if tonight else ""
        plays_section = self._build_plays(digest)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:{self.colors['bg']};">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:{self.colors['bg']};">
        {masthead}
        {headline_section}
        {games_section}
        {series_section}
        {recaps_section}
        {headlines_section}
        {performances_section}
        {tonight_section}
        {plays_section}
    </table>
</body>
</html>"""

        return html

    def _build_masthead(self, digest: Digest) -> str:
        """Build page masthead with title and date."""
        return f"""<tr><td style="padding:32px 32px 0; text-align:center;">
            <p style="font-size:11px; letter-spacing:3px; text-transform:uppercase;
                       color:{self.colors['textFaint']}; margin:0 0 6px;
                       font-family:Helvetica,Arial,sans-serif;">Daily briefing</p>
            <h1 style="font-size:28px; font-weight:normal; color:{self.colors['text']};
                        margin:0; letter-spacing:-0.5px; line-height:1.15;
                        font-family:Georgia,'Times New Roman',serif;">
                NBA Playoff Digest</h1>
            <div style="width:40px; height:2px; background:{self.colors['text']};
                         margin:14px auto;"></div>
            <p style="font-size:13px; color:{self.colors['textMuted']}; margin:0;
                       font-family:Helvetica,Arial,sans-serif;">
                {escape(digest.date)} &middot; {escape(digest.round)}</p>
        </td></tr>"""

    def _build_headline(self, digest: Digest) -> str:
        """Build main and sub headlines."""
        return f"""<tr><td style="padding:20px 32px 24px; text-align:center;">
            <h2 style="font-size:21px; font-weight:normal; color:{self.colors['text']};
                        margin:0 0 6px; line-height:1.3;
                        font-family:Georgia,'Times New Roman',serif;">
                {escape(digest.main_headline)}</h2>
            <p style="font-size:14px; color:{self.colors['textMuted']}; margin:0;
                       font-style:italic; line-height:1.5;
                       font-family:Georgia,'Times New Roman',serif;">
                {escape(digest.sub_headline)}</p>
        </td></tr>"""

    def _build_games(self, digest: Digest) -> str:
        """Build tonight's game results."""
        if not digest.games:
            return ""

        games_html = ""
        for game in digest.games:
            games_html += f"""<div style="background:{self.colors['surface']}; border-radius:5px;
                            padding:10px 14px; margin-bottom:8px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="font-size:14px; font-weight:bold; color:{self.colors['text']};
                                    font-family:Georgia,serif;">
                            {escape(game.winner_abbr)} {escape(game.winner_name)}
                            <span style="font-size:10px; font-weight:normal; font-style:italic;
                                          color:{self.colors['textMuted']}; padding-left:6px;
                                          font-family:Helvetica,Arial,sans-serif;">
                                {escape(game.series_status)}</span>
                        </td>
                        <td style="text-align:right; font-size:17px; font-weight:bold;
                                    color:{self.colors['text']}; font-family:Georgia,serif;">
                            {game.winner_score}</td>
                    </tr>
                    <tr>
                        <td style="font-size:14px; color:{self.colors['textMuted']};
                                    font-family:Georgia,serif; padding-top:2px;">
                            {escape(game.loser_abbr)} {escape(game.loser_name)}</td>
                        <td style="text-align:right; font-size:17px; color:{self.colors['textMuted']};
                                    font-family:Georgia,serif; padding-top:2px;">
                            {game.loser_score}</td>
                    </tr>
                </table>
            </div>"""

        return f"""<tr><td style="padding:24px 32px;">
            <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                       color:{self.colors['textFaint']}; margin:0 0 16px;
                       font-family:Helvetica,Arial,sans-serif;">Tonight's results</p>
            {games_html}
        </td></tr>"""

    def _build_series(self, digest: Digest) -> str:
        """Build active series standings."""
        if not digest.active_series:
            return ""
        # Full implementation would build East/West columns with pip dots
        return ""

    def _build_recaps(self, digest: Digest) -> str:
        """Build game recaps section."""
        if not digest.recaps:
            return ""

        recaps_html = ""
        for recap in digest.recaps:
            recaps_html += f"""<div style="margin-bottom:20px;">
                <p style="font-size:13px; font-weight:bold; color:{self.colors['text']};
                           margin:0 0 6px; font-family:Helvetica,Arial,sans-serif;">
                    {escape(recap.title)}</p>
                <p style="font-size:14px; color:{self.colors['textMid']}; margin:0;
                           line-height:1.7; font-family:Georgia,'Times New Roman',serif;">
                    {escape(recap.body)}</p>
            </div>"""

        return f"""<tr><td style="padding:24px 32px;">
            <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                       color:{self.colors['textFaint']}; margin:0 0 16px;
                       font-family:Helvetica,Arial,sans-serif;">Game recaps</p>
            {recaps_html}
        </td></tr>"""

    def _build_headlines(self, digest: Digest) -> str:
        """Build headlines and narratives section."""
        if not digest.headlines:
            return ""

        headlines_html = ""
        for headline in digest.headlines:
            headlines_html += f"""<p style="font-size:14px; color:{self.colors['textMid']};
                           line-height:1.7; margin:0 0 12px;
                           font-family:Georgia,'Times New Roman',serif;">
                <span style="font-weight:bold; color:{self.colors['text']};">
                    {escape(headline.bold_lead)}</span> {escape(headline.body)}</p>"""

        return f"""<tr><td style="padding:24px 32px;">
            <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                       color:{self.colors['textFaint']}; margin:0 0 14px;
                       font-family:Helvetica,Arial,sans-serif;">Headlines &amp; narratives</p>
            {headlines_html}
        </td></tr>"""

    def _build_performances(self, digest: Digest) -> str:
        """Build standout performances section."""
        if not digest.standout_performances:
            return ""
        # Full implementation would include player headshots from cdn.nba.com
        return ""

    def _build_tonight(self, tonight: List[Dict[str, Any]]) -> str:
        """Build tonight's games section."""
        if not tonight:
            return ""
        # Full implementation would list pre-game matchups with series status
        return ""

    def _build_plays(self, digest: Digest) -> str:
        """Build Plays of the Night link."""
        if not digest.plays_of_night_url:
            return ""

        return f"""<tr><td style="padding:24px 32px; text-align:center;">
            <a href="{escape(digest.plays_of_night_url)}"
               style="display:inline-block; font-size:12px;
                       letter-spacing:1px; text-transform:uppercase; text-decoration:none;
                       color:{self.colors['text']}; border-bottom:1px solid {self.colors['text']};
                       padding-bottom:2px; font-family:Helvetica,Arial,sans-serif;">
                ▶ Plays of the Night</a>
        </td></tr>"""
