#!/usr/bin/env python3
"""
NBA Playoff Nightly Digest
Fetches today's NBA playoff results via Claude API + web search,
then emails a beautifully formatted e-ink style digest to your inbox.

Setup:
  1. pip install anthropic
  2. Export your Anthropic API key:
       export ANTHROPIC_API_KEY="sk-ant-..."
  3. Create a Gmail App Password (not your regular password):
       Google Account → Security → 2-Step Verification → App Passwords
       Generate one for "Mail" and export it:
       export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
  4. Run it:
       python3 nba_digest.py
  5. Automate with cron (e.g. every night at 10:30 PM PT):
       crontab -e
       30 22 * * * cd /home/keaton/nba-digest && /usr/bin/python3 nba_digest.py >> digest.log 2>&1

Environment variables:
  ANTHROPIC_API_KEY   - Your Anthropic API key
  GMAIL_APP_PASSWORD  - Gmail app password (NOT your Google password)
  DIGEST_EMAIL        - Recipient email (defaults to rentapolo@gmail.com)
  SENDER_EMAIL        - Sender email (defaults to same as DIGEST_EMAIL)
"""

import json
import os
import sys
import smtplib
import logging
import time
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

import anthropic

# ── Config ──────────────────────────────────────────────────────────────

RECIPIENT = os.environ.get("DIGEST_EMAIL", "rentapolo@gmail.com")
SENDER = os.environ.get("SENDER_EMAIL", RECIPIENT)
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CACHE_DIR = Path(os.environ.get("DIGEST_CACHE_DIR", os.path.expanduser("~/nba-digest/cache")))
MAX_RETRIES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("nba-digest")


# ── Reddit Pre-Fetch ───────────────────────────────────────────────────

def fetch_reddit_posts(limit: int = 25) -> str:
    """Fetch top posts from r/nba. Returns formatted text or empty string on failure."""
    url = f"https://www.reddit.com/r/nba/hot.json?limit={limit}"
    req = urllib.request.Request(url, headers={"User-Agent": "NBADigest/2.0"})

    try:
        log.info("Fetching r/nba posts...")
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        posts = []
        for child in data.get("data", {}).get("children", []):
            p = child.get("data", {})
            if p.get("stickied"):
                continue
            flair = p.get("link_flair_text", "") or ""
            title = p.get("title", "")
            score = p.get("score", 0)
            comments = p.get("num_comments", 0)
            selftext = (p.get("selftext", "") or "")[:200]
            posts.append(
                f"[{flair}] {title} ({score} pts, {comments} comments)"
                + (f"\n  {selftext}" if selftext else "")
            )

        result = "\n".join(posts[:25])
        log.info("Fetched %d r/nba posts", len(posts))
        return result

    except Exception as e:
        log.warning("Reddit fetch failed (non-fatal): %s", e)
        return ""

# ── Colors (e-ink / Kindle palette) ────────────────────────────────────

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

# ── Digest Generation ──────────────────────────────────────────────────

DIGEST_PROMPT = """Today is {date_str}. You are generating a structured NBA playoff digest covering last night's completed games.

{reddit_block}

Search for:
1. "NBA playoff scores results standings highlights performances {iso_date}"

Then return ONLY a JSON object (no markdown, no backticks, no preamble) with this exact structure:

{{
  "date": "{date_str}",
  "round": "First Round",
  "main_headline": "...",
  "sub_headline": "...",
  "games": [
    {{
      "winner_abbr": "ATL",
      "winner_name": "Hawks",
      "winner_score": 107,
      "loser_abbr": "NYK",
      "loser_name": "Knicks",
      "loser_score": 106,
      "game_number": 3,
      "venue": "State Farm Arena, Atlanta",
      "series_status": "ATL leads 2-1",
      "pts_leader": "McCollum 23",
      "reb_leader": "Johnson 10",
      "ast_leader": "Barnes 11"
    }}
  ],
  "active_series": [
    {{ "conference": "East", "team1": "DET", "team1_wins": 1, "team2": "ORL", "team2_wins": 1 }},
    {{ "conference": "West", "team1": "OKC", "team1_wins": 2, "team2": "MEM", "team2_wins": 0 }}
  ],
  "recaps": [
    {{
      "title": "Hawks 107, Knicks 106 — Game 3",
      "body": "2-6 sentence narrative recap. Tight for close games, shorter for blowouts."
    }}
  ],
  "headlines": [
    {{
      "bold_lead": "Short bold intro.",
      "body": "1-2 sentence explanation."
    }}
  ],
  "standout_performances": [
    {{
      "name": "Scottie Barnes",
      "context": "in Game 3 win",
      "stats": "33 pts · 5 reb · 11 ast",
      "note": "Dominated from start to finish",
      "player_id": "1630567",
      "highlight_url": "https://www.youtube.com/watch?v=..."
    }}
  ]
}}

Important notes:
- The digest covers LAST NIGHT'S completed games, not upcoming games. The main_headline and sub_headline should reflect what already happened.
- For player_id, use the NBA.com player ID number (the one used at cdn.nba.com/headshots/nba/latest/260x190/PLAYER_ID.png). Look these up accurately.
- Include ALL games played last night. If no games were played, set games to an empty array and note it in the headline.
- For active_series, include all series with their current win totals. Each series MUST include "conference": "East" or "conference": "West".
- For recaps, write like a basketball writer — capture momentum shifts, key runs, and what decided the game. Use the mix approach: tight 2-3 sentences for blowouts, narrative 4-6 sentences for close games.
- For headlines, capture the biggest talking points, controversies, injury news, and r/nba discourse.
- For standout_performances, pick the 3-5 best individual performances from last night. For highlight_url, search for a real YouTube or NBA.com highlight clip URL for each player. If you can't find one, omit the field.
- Return ONLY valid JSON. No markdown fences. No explanation text."""


def generate_digest() -> dict:
    """Call Claude API with web search + Reddit context. Retries up to MAX_RETRIES times.
    Caches successful results to disk."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    now = datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    iso_date = now.strftime("%Y-%m-%d")

    # Pre-fetch Reddit (no CORS issues in Python)
    reddit_posts = fetch_reddit_posts()
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

    prompt = DIGEST_PROMPT.format(
        date_str=date_str, iso_date=iso_date, reddit_block=reddit_block
    )

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("Calling Claude API (attempt %d/%d)...", attempt, MAX_RETRIES)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text blocks
            text_parts = []
            for block in response.content:
                if block.type == "text" and block.text:
                    text_parts.append(block.text)

            raw = "\n".join(text_parts).strip()
            raw = raw.replace("```json", "").replace("```", "").strip()

            if not raw:
                raise RuntimeError("Claude returned no text content")

            # Extract JSON object from response (handles narration before/after)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise json.JSONDecodeError("No JSON object found", raw, 0)
            raw = raw[start:end]

            digest = json.loads(raw)
            log.info("Digest generated with %d games", len(digest.get("games", [])))

            # Cache to disk
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f"digest-{iso_date}.json"
            cache_file.write_text(json.dumps(digest, indent=2))
            log.info("Cached digest to %s", cache_file)

            return digest

        except json.JSONDecodeError as e:
            last_error = e
            log.warning(
                "Attempt %d: JSON parse failed: %s (raw: %s...)",
                attempt, e, raw[:200] if raw else "empty",
            )
            if attempt < MAX_RETRIES:
                time.sleep(30 * attempt)
        except Exception as e:
            last_error = e
            log.warning("Attempt %d failed: %s", attempt, e)
            if attempt < MAX_RETRIES:
                # Use longer backoff for rate limits
                backoff = 60 if "429" in str(e) or "rate_limit" in str(e) else 10 * attempt
                log.info("Waiting %ds before retry...", backoff)
                time.sleep(backoff)

    raise RuntimeError(f"All {MAX_RETRIES} attempts failed. Last error: {last_error}")


# ── HTML Email Builder ─────────────────────────────────────────────────

def _divider() -> str:
    return f'''<tr><td style="padding: 0 32px;">
        <div style="height: 1px; background: {INK["border"]};"></div>
    </td></tr>'''


def build_email_html(d: dict) -> str:
    """Build the full e-ink styled HTML email from structured digest data."""

    masthead = f'''
    <tr><td style="padding: 32px 32px 0; text-align: center;">
        <p style="font-size:11px; letter-spacing:3px; text-transform:uppercase;
                   color:{INK["textFaint"]}; margin:0 0 6px;
                   font-family:Helvetica,Arial,sans-serif;">Nightly briefing</p>
        <h1 style="font-size:28px; font-weight:normal; color:{INK["text"]};
                    margin:0; letter-spacing:-0.5px; line-height:1.15;
                    font-family:Georgia,'Times New Roman',serif;">
            NBA Playoff Digest</h1>
        <div style="width:40px; height:2px; background:{INK["text"]};
                     margin:14px auto;"></div>
        <p style="font-size:13px; color:{INK["textMuted"]}; margin:0;
                   font-family:Helvetica,Arial,sans-serif;">
            {d.get("date", "")} &middot; {d.get("round", "Playoffs")}</p>
    </td></tr>'''

    headline_section = f'''
    <tr><td style="padding:20px 32px 24px; text-align:center;">
        <h2 style="font-size:21px; font-weight:normal; color:{INK["text"]};
                    margin:0 0 6px; line-height:1.3;
                    font-family:Georgia,'Times New Roman',serif;">
            {d.get("main_headline", "")}</h2>
        <p style="font-size:14px; color:{INK["textMuted"]}; margin:0;
                   font-style:italic; line-height:1.5;
                   font-family:Georgia,'Times New Roman',serif;">
            {d.get("sub_headline", "")}</p>
    </td></tr>'''

    # ── Tonight's results ──
    games_html = ""
    for i, g in enumerate(d.get("games", [])):
        mb = "22px" if i < len(d["games"]) - 1 else "0"
        games_html += f'''
        <div style="margin-bottom:{mb};">
            <p style="font-size:11px; color:{INK["textFaint"]}; margin:0 0 8px;
                       font-family:Helvetica,Arial,sans-serif;">
                {d.get("round", "")} &middot; Game {g.get("game_number", "")}
                &middot; {g.get("venue", "")}</p>
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td style="font-size:15px; color:{INK["text"]}; font-weight:bold;
                                font-family:Georgia,serif; padding:0 0 2px;">
                        {g.get("winner_abbr", "")} {g.get("winner_name", "")}
                        <span style="font-size:11px; color:{INK["textMuted"]};
                                      font-weight:normal; font-style:italic;
                                      font-family:Helvetica,Arial,sans-serif;
                                      padding-left:8px;">
                            {g.get("series_status", "")}</span>
                    </td>
                    <td style="text-align:right; font-size:18px; color:{INK["text"]};
                                font-weight:bold; font-family:Georgia,serif; padding:0 0 2px;">
                        {g.get("winner_score", "")}</td>
                </tr>
                <tr>
                    <td style="font-size:15px; color:{INK["textMuted"]};
                                font-family:Georgia,serif; padding:0 0 8px;">
                        {g.get("loser_abbr", "")} {g.get("loser_name", "")}</td>
                    <td style="text-align:right; font-size:18px; color:{INK["textMuted"]};
                                font-family:Georgia,serif; padding:0 0 8px;">
                        {g.get("loser_score", "")}</td>
                </tr>
            </table>
            <p style="font-size:11px; color:{INK["textFaint"]}; margin:0;
                       font-family:Helvetica,Arial,sans-serif; line-height:1.6;">
                Pts: {g.get("pts_leader", "")}
                <span style="color:{INK["border"]};">&nbsp;&middot;&nbsp;</span>
                Reb: {g.get("reb_leader", "")}
                <span style="color:{INK["border"]};">&nbsp;&middot;&nbsp;</span>
                Ast: {g.get("ast_leader", "")}</p>
        </div>'''

    results_section = f'''
    <tr><td style="padding:24px 32px;">
        <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                   color:{INK["textFaint"]}; margin:0 0 16px;
                   font-family:Helvetica,Arial,sans-serif;">Last night's results</p>
        {games_html}
    </td></tr>''' if d.get("games") else ""

    # ── Active series grouped by conference ──
    series_list = d.get("active_series", [])

    def _series_conf_block(conf_label, series):
        rows_html = ""
        for row_start in range(0, len(series), 4):
            row_cells = ""
            chunk = series[row_start:row_start + 4]
            for sr in chunk:
                row_cells += f'''
                    <td style="background:{INK["surface"]}; border-radius:5px;
                                padding:8px 6px; text-align:center;">
                        <p style="font-size:12px; font-weight:bold; color:{INK["text"]};
                                   margin:0; font-family:Helvetica,Arial,sans-serif;">
                            {sr.get("team1", "")} {sr.get("team1_wins", 0)}</p>
                        <p style="font-size:12px; color:{INK["textMuted"]};
                                   margin:1px 0 0; font-family:Helvetica,Arial,sans-serif;">
                            {sr.get("team2", "")} {sr.get("team2_wins", 0)}</p>
                    </td>'''
            row_cells += "<td></td>" * (4 - len(chunk))
            mb = "8px" if row_start + 4 < len(series) else "0"
            rows_html += f'''
                <table width="100%" cellpadding="0" cellspacing="4"
                       style="margin-bottom:{mb};">
                    <tr>{row_cells}</tr>
                </table>'''
        return f'''
        <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                   color:{INK["textFaint"]}; margin:0 0 8px;
                   font-family:Helvetica,Arial,sans-serif;">{conf_label}</p>
        {rows_html}'''

    east = [s for s in series_list if s.get("conference", "").lower() == "east"]
    west = [s for s in series_list if s.get("conference", "").lower() == "west"]
    other = [s for s in series_list if s.get("conference", "").lower() not in ("east", "west")]

    series_rows_html = ""
    if east:
        series_rows_html += _series_conf_block("Eastern Conference", east)
    if west:
        if east:
            series_rows_html += f'<div style="margin-top:16px;"></div>'
        series_rows_html += _series_conf_block("Western Conference", west)
    if other:
        series_rows_html += _series_conf_block("Playoffs", other)

    series_section = f'''
    <tr><td style="padding:20px 32px;">
        <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                   color:{INK["textFaint"]}; margin:0 0 12px;
                   font-family:Helvetica,Arial,sans-serif;">Active series</p>
        {series_rows_html}
    </td></tr>''' if series_list else ""

    # ── Game recaps ──
    recaps_html = ""
    for i, r in enumerate(d.get("recaps", [])):
        mb = "20px" if i < len(d["recaps"]) - 1 else "0"
        recaps_html += f'''
        <div style="margin-bottom:{mb};">
            <p style="font-size:13px; font-weight:bold; color:{INK["text"]};
                       margin:0 0 6px; font-family:Helvetica,Arial,sans-serif;">
                {r.get("title", "")}</p>
            <p style="font-size:14px; color:{INK["textMid"]}; margin:0;
                       line-height:1.7; font-family:Georgia,'Times New Roman',serif;">
                {r.get("body", "")}</p>
        </div>'''

    recaps_section = f'''
    <tr><td style="padding:24px 32px;">
        <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                   color:{INK["textFaint"]}; margin:0 0 16px;
                   font-family:Helvetica,Arial,sans-serif;">Game recaps</p>
        {recaps_html}
    </td></tr>''' if d.get("recaps") else ""

    # ── Headlines ──
    headlines_html = ""
    for i, h in enumerate(d.get("headlines", [])):
        mb = "12px" if i < len(d["headlines"]) - 1 else "0"
        headlines_html += f'''
        <p style="font-size:14px; color:{INK["textMid"]}; line-height:1.7;
                   margin:0 0 {mb}; font-family:Georgia,'Times New Roman',serif;">
            <span style="font-weight:bold; color:{INK["text"]};">
                {h.get("bold_lead", "")}</span> {h.get("body", "")}</p>'''

    headlines_section = f'''
    <tr><td style="padding:24px 32px;">
        <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                   color:{INK["textFaint"]}; margin:0 0 14px;
                   font-family:Helvetica,Arial,sans-serif;">Headlines &amp; narratives</p>
        {headlines_html}
    </td></tr>''' if d.get("headlines") else ""

    # ── Standout performances ──
    perfs_html = ""
    for p in d.get("standout_performances", []):
        pid = p.get("player_id", "")
        img_html = ""
        if pid:
            img_html = f'''
                <td width="48" style="padding-right:14px; vertical-align:middle;">
                    <img src="https://cdn.nba.com/headshots/nba/latest/260x190/{pid}.png"
                         alt="{p.get('name', '')}" width="48" height="48"
                         style="border-radius:50%; display:block;
                                background:#ddd7c9;" />
                </td>'''

        perfs_html += f'''
        <table width="100%" cellpadding="0" cellspacing="0"
               style="background:{INK["surface"]}; border-radius:6px;
                      margin-bottom:14px;">
            <tr><td style="padding:12px 14px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        {img_html}
                        <td style="vertical-align:middle;">
                            <p style="font-size:14px; font-weight:bold;
                                       color:{INK["text"]}; margin:0;
                                       font-family:Georgia,serif;">
                                {p.get("name", "")}
                                <span style="font-weight:normal; font-size:12px;
                                              color:{INK["textMuted"]};">
                                    {p.get("context", "")}</span></p>
                            <p style="font-size:16px; color:{INK["text"]};
                                       margin:4px 0 0; font-weight:bold;
                                       font-family:Helvetica,Arial,sans-serif;">
                                {p.get("stats", "")}</p>
                            <p style="font-size:11px; color:{INK["textMuted"]};
                                       margin:4px 0 0; font-style:italic;
                                       font-family:Helvetica,Arial,sans-serif;">
                                {p.get("note", "")}</p>
                            {f'''<a href="{p["highlight_url"]}" style="display:inline-block; margin-top:8px;
                                       font-size:10px; letter-spacing:1.5px; text-transform:uppercase;
                                       color:{INK["textMuted"]}; text-decoration:none;
                                       border:1px solid {INK["border"]}; border-radius:3px;
                                       padding:3px 8px; font-family:Helvetica,Arial,sans-serif;">
                                ▶ Highlights</a>''' if p.get("highlight_url") else ""}
                        </td>
                    </tr>
                </table>
            </td></tr>
        </table>'''

    perfs_section = f'''
    <tr><td style="padding:24px 32px;">
        <p style="font-size:10px; letter-spacing:2.5px; text-transform:uppercase;
                   color:{INK["textFaint"]}; margin:0 0 14px;
                   font-family:Helvetica,Arial,sans-serif;">Standout performances</p>
        {perfs_html}
    </td></tr>''' if d.get("standout_performances") else ""

    footer = f'''
    <tr><td style="padding:20px 32px; text-align:center;
                    border-top:1px solid {INK["border"]};">
        <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                   color:{INK["textGhost"]}; margin:0;
                   font-family:Helvetica,Arial,sans-serif;">
            Generated by Claude &middot; No social media required</p>
    </td></tr>'''

    # Assemble
    sections = [masthead, headline_section, _divider()]
    if results_section:
        sections += [results_section, _divider()]
    if series_section:
        sections += [series_section, _divider()]
    if recaps_section:
        sections += [recaps_section, _divider()]
    if headlines_section:
        sections += [headlines_section, _divider()]
    if perfs_section:
        sections += [perfs_section]
    sections.append(footer)

    rows = "\n".join(sections)

    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#e8e3db;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#e8e3db;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background-color:{INK["bg"]}; border-radius:8px; overflow:hidden;">
          {rows}
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def build_plaintext(d: dict) -> str:
    """Build a plaintext fallback from the digest dict."""
    lines = [
        "NBA PLAYOFF DIGEST",
        f"{d.get('date', '')} · {d.get('round', '')}",
        "",
        d.get("main_headline", ""),
        d.get("sub_headline", ""),
        "",
    ]

    if d.get("games"):
        lines.append("TONIGHT'S RESULTS")
        lines.append("-" * 40)
        for g in d["games"]:
            lines.append(
                f"{g['winner_abbr']} {g['winner_name']} {g['winner_score']}, "
                f"{g['loser_abbr']} {g['loser_name']} {g['loser_score']} "
                f"(Game {g['game_number']}) — {g['series_status']}"
            )
            lines.append(
                f"  Pts: {g['pts_leader']} · Reb: {g['reb_leader']} "
                f"· Ast: {g['ast_leader']}"
            )
            lines.append(f"  {g['venue']}")
            lines.append("")

    if d.get("active_series"):
        lines.append("ACTIVE SERIES")
        lines.append("-" * 40)
        for sr in d["active_series"]:
            lines.append(
                f"  {sr['team1']} {sr['team1_wins']} - "
                f"{sr['team2']} {sr['team2_wins']}"
            )
        lines.append("")

    if d.get("recaps"):
        lines.append("GAME RECAPS")
        lines.append("-" * 40)
        for r in d["recaps"]:
            lines.append(r["title"])
            lines.append(r["body"])
            lines.append("")

    if d.get("headlines"):
        lines.append("HEADLINES & NARRATIVES")
        lines.append("-" * 40)
        for h in d["headlines"]:
            lines.append(f"{h['bold_lead']} {h['body']}")
            lines.append("")

    if d.get("standout_performances"):
        lines.append("STANDOUT PERFORMANCES")
        lines.append("-" * 40)
        for p in d["standout_performances"]:
            lines.append(f"{p['name']} ({p['context']}): {p['stats']}")
            lines.append(f"  {p['note']}")
            lines.append("")

    lines.append("Generated by Claude · No social media required")
    return "\n".join(lines)


# ── Email ──────────────────────────────────────────────────────────────

def send_email(subject: str, html_body: str, text_body: str):
    """Send the digest via Gmail SMTP."""
    if not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_APP_PASSWORD not set. "
            "Create one at: Google Account → Security → App Passwords"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"NBA Digest <{SENDER}>"
    msg["To"] = RECIPIENT

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    log.info("Sending email to %s...", RECIPIENT)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, GMAIL_APP_PASSWORD)
        server.sendmail(SENDER, RECIPIENT, msg.as_string())

    log.info("Email sent successfully")


# ── Season Mode Detection ─────────────────────────────────────────────

# Approximate NBA calendar (adjust yearly as needed)
SEASON_CALENDAR = {
    # (month, day) ranges — inclusive
    "playoffs":        ((4, 15), (6, 25)),    # mid-Apr through late Jun
    "offseason":       ((6, 26), (10, 14)),   # late Jun through mid-Oct
    "regular_season":  ((10, 15), (4, 14)),   # mid-Oct through mid-Apr
}


def get_season_mode(now: datetime = None) -> str:
    """Return 'playoffs', 'offseason', or 'regular_season'."""
    now = now or datetime.now()
    md = (now.month, now.day)

    for mode, ((s_m, s_d), (e_m, e_d)) in SEASON_CALENDAR.items():
        if s_m <= e_m:
            # Same-year range (e.g. Apr-Jun)
            if (s_m, s_d) <= md <= (e_m, e_d):
                return mode
        else:
            # Wraps around year boundary (e.g. Oct-Apr)
            if md >= (s_m, s_d) or md <= (e_m, e_d):
                return mode

    return "regular_season"


def should_run_today(mode: str, now: datetime = None) -> bool:
    """Offseason: only run on Mondays. Otherwise: run daily."""
    now = now or datetime.now()
    if mode == "offseason":
        return now.weekday() == 0  # Monday
    return True


# ── Season-Specific Prompts ───────────────────────────────────────────

OFFSEASON_PROMPT = """Today is {date_str}. You are generating a weekly NBA offseason digest.

{reddit_block}

Search for:
1. "NBA offseason news trades free agency draft highlights {iso_date}"

Return ONLY a JSON object (no markdown, no backticks) with this structure:

{{
  "date": "{date_str}",
  "round": "Offseason",
  "main_headline": "The biggest NBA story this week",
  "sub_headline": "One-liner editorial subheadline",
  "games": [],
  "active_series": [],
  "recaps": [],
  "headlines": [
    {{
      "bold_lead": "Short bold intro.",
      "body": "1-2 sentence explanation."
    }}
  ],
  "standout_performances": []
}}

Include 4-6 headlines covering the week's biggest stories: trades, free agency,
draft news, coaching changes, r/nba discourse, and anything fans are talking about.
Return ONLY valid JSON."""

REGULAR_SEASON_PROMPT = """Today is {date_str}. You are generating a nightly NBA regular season digest covering last night's completed games.

{reddit_block}

Search for:
1. "NBA scores results standings highlights performances {iso_date}"

Return ONLY a JSON object (no markdown, no backticks) with this exact structure:

{{
  "date": "{date_str}",
  "round": "Regular Season",
  "main_headline": "...",
  "sub_headline": "...",
  "games": [
    {{
      "winner_abbr": "BOS",
      "winner_name": "Celtics",
      "winner_score": 118,
      "loser_abbr": "MIL",
      "loser_name": "Bucks",
      "loser_score": 104,
      "game_number": 0,
      "venue": "TD Garden, Boston",
      "series_status": "BOS: 42-12",
      "pts_leader": "Tatum 34",
      "reb_leader": "Giannis 14",
      "ast_leader": "Holiday 11"
    }}
  ],
  "active_series": [],
  "recaps": [
    {{
      "title": "Celtics 118, Bucks 104",
      "body": "Brief 2-3 sentence recap."
    }}
  ],
  "headlines": [
    {{
      "bold_lead": "Short bold intro.",
      "body": "1-2 sentence explanation."
    }}
  ],
  "standout_performances": [
    {{
      "name": "Jayson Tatum",
      "context": "vs Bucks",
      "stats": "34 pts · 8 reb · 5 ast",
      "note": "Career-high 8 threes",
      "player_id": "1628369"
    }}
  ]
}}

Important notes:
- The digest covers LAST NIGHT'S completed games. The main_headline should reflect what already happened.
- For series_status during regular season, show the WINNING team's record (e.g. "BOS: 42-12").
- Include the most notable 3-5 games (skip unremarkable blowouts if there are many games).
- For player_id, use the NBA.com player ID.
- Return ONLY valid JSON."""


def get_prompt_for_mode(mode: str) -> str:
    """Return the appropriate prompt template for the current season mode."""
    if mode == "offseason":
        return OFFSEASON_PROMPT
    elif mode == "regular_season":
        return REGULAR_SEASON_PROMPT
    else:
        return DIGEST_PROMPT


# ── Blog / GitHub Pages ────────────────────────────────────────────────

DOCS_DIR = Path(os.environ.get("DOCS_DIR", "docs"))


def build_page_html(digest: dict, html_body: str, iso_date: str) -> str:
    """Wrap the email HTML in a minimal page shell with nav."""
    prev_date = None
    next_date = None
    all_pages = sorted(DOCS_DIR.glob("????-??-??.html"))
    dates = [p.stem for p in all_pages]
    if iso_date in dates:
        idx = dates.index(iso_date)
        if idx > 0:
            prev_date = dates[idx - 1]
        if idx < len(dates) - 1:
            next_date = dates[idx + 1]

    nav_links = []
    if prev_date:
        nav_links.append(f'<a href="{prev_date}.html" style="color:{INK["textMuted"]}; text-decoration:none;">← {prev_date}</a>')
    nav_links.append(f'<a href="index.html" style="color:{INK["textMuted"]}; text-decoration:none;">All digests</a>')
    if next_date:
        nav_links.append(f'<a href="{next_date}.html" style="color:{INK["textMuted"]}; text-decoration:none;">{next_date} →</a>')

    nav_html = f'''
    <div style="max-width:632px; margin:0 auto; padding:16px 16px 0;
                display:flex; justify-content:space-between; align-items:center;
                font-size:11px; font-family:Helvetica,Arial,sans-serif;
                color:{INK["textMuted"]};">
        {"&nbsp;&nbsp;&nbsp;".join(nav_links)}
    </div>'''

    inner = html_body.replace(
        '<body style="margin:0; padding:0; background-color:#e8e3db;">',
        f'<body style="margin:0; padding:0; background-color:#e8e3db;">{nav_html}'
    )
    return inner


def save_page(digest: dict, html_body: str, iso_date: str):
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    page_html = build_page_html(digest, html_body, iso_date)
    page_file = DOCS_DIR / f"{iso_date}.html"
    page_file.write_text(page_html)
    log.info("Saved page to %s", page_file)


def build_index_html() -> str:
    entries = []
    for cache_file in sorted(DOCS_DIR.glob("????-??-??.html"), reverse=True):
        iso = cache_file.stem
        json_file = CACHE_DIR / f"digest-{iso}.json"
        headline = ""
        round_label = ""
        if json_file.exists():
            try:
                d = json.loads(json_file.read_text())
                headline = d.get("main_headline", "")
                round_label = d.get("round", "")
            except Exception:
                pass
        entries.append((iso, headline, round_label))

    rows_html = ""
    for iso, headline, round_label in entries:
        rows_html += f'''
        <a href="{iso}.html" style="display:block; text-decoration:none;
                  border-bottom:1px solid {INK["border"]}; padding:14px 0;">
            <p style="font-size:10px; letter-spacing:2px; text-transform:uppercase;
                       color:{INK["textFaint"]}; margin:0 0 4px;
                       font-family:Helvetica,Arial,sans-serif;">{iso} &middot; {round_label}</p>
            <p style="font-size:15px; color:{INK["text"]}; margin:0; line-height:1.4;
                       font-family:Georgia,'Times New Roman',serif;">{headline or "NBA Digest"}</p>
        </a>'''

    return f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NBA Digest Archive</title>
</head>
<body style="margin:0; padding:0; background-color:#e8e3db;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#e8e3db;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background-color:{INK["bg"]}; border-radius:8px; overflow:hidden;">
          <tr><td style="padding:32px 32px 8px; text-align:center;">
            <p style="font-size:11px; letter-spacing:3px; text-transform:uppercase;
                       color:{INK["textFaint"]}; margin:0 0 6px;
                       font-family:Helvetica,Arial,sans-serif;">Archive</p>
            <h1 style="font-size:26px; font-weight:normal; color:{INK["text"]};
                        margin:0; font-family:Georgia,'Times New Roman',serif;">
                NBA Digest</h1>
            <div style="width:40px; height:2px; background:{INK["text"]}; margin:14px auto;"></div>
          </td></tr>
          <tr><td style="padding:8px 32px 32px;">
            {rows_html if rows_html else '<p style="color:#888; font-family:Helvetica,Arial,sans-serif; font-size:13px;">No digests yet.</p>'}
          </td></tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>'''


def update_index():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    index_file = DOCS_DIR / "index.html"
    index_file.write_text(build_index_html())
    log.info("Updated index at %s", index_file)


# ── Main ───────────────────────────────────────────────────────────────

def main():
    try:
        now = datetime.now()
        mode = get_season_mode(now)
        log.info("Season mode: %s", mode)

        if not should_run_today(mode, now):
            log.info("Offseason — not Monday, skipping. Next run Monday.")
            return

        date_short = now.strftime("%A, %B %-d")

        # Override the global prompt based on season mode
        global DIGEST_PROMPT
        original_prompt = DIGEST_PROMPT
        DIGEST_PROMPT = get_prompt_for_mode(mode)

        digest = generate_digest()

        # Restore
        DIGEST_PROMPT = original_prompt

        iso_date = now.strftime("%Y-%m-%d")

        # Adjust subject line
        mode_labels = {
            "playoffs": "Playoff Digest",
            "regular_season": "Nightly Digest",
            "offseason": "Weekly Roundup",
        }
        label = mode_labels.get(mode, "Digest")
        subject = f"\U0001f3c0 NBA {label} — {date_short}"

        html_body = build_email_html(digest)
        text_body = build_plaintext(digest)

        send_email(subject, html_body, text_body)

        save_page(digest, html_body, iso_date)
        update_index()

        log.info("Done!")

    except Exception as e:
        log.error("Failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
