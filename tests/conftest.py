"""Pytest fixtures for NBA Digest tests."""

import pytest
from nba_digest.models import Digest, Game, ActiveSeries, Recap, Headline, StandoutPerformance


@pytest.fixture
def sample_game() -> Game:
    """Sample game fixture."""
    return Game(
        winner_abbr="ATL",
        winner_name="Hawks",
        winner_score=107,
        loser_abbr="NYK",
        loser_name="Knicks",
        loser_score=106,
        game_number=3,
        venue="State Farm Arena, Atlanta",
        series_status="ATL leads 2-1",
        pts_leader="McCollum 23",
        reb_leader="Johnson 10",
        ast_leader="Barnes 11",
    )


@pytest.fixture
def sample_series() -> ActiveSeries:
    """Sample series fixture."""
    return ActiveSeries(
        conference="East",
        top_seed=4,
        team1="DET",
        team1_wins=1,
        team2="ORL",
        team2_wins=1,
    )


@pytest.fixture
def sample_recap() -> Recap:
    """Sample recap fixture."""
    return Recap(
        title="Hawks 107, Knicks 106 — Game 3",
        body="Atlanta stun New York in a thrilling Game 3 to take series lead.",
    )


@pytest.fixture
def sample_headline() -> Headline:
    """Sample headline fixture."""
    return Headline(
        bold_lead="Hawks stun Knicks in Game 3.",
        body="Atlanta's defensive pressure in final minutes proved decisive.",
    )


@pytest.fixture
def sample_performance() -> StandoutPerformance:
    """Sample player performance fixture."""
    return StandoutPerformance(
        name="CJ McCollum",
        context="in Game 3 win vs. Pistons",
        stats="28 pts · 6 ast",
        note="Hit crucial late-game three-pointers",
        player_id="203507",
        highlight_url="https://www.youtube.com/watch?v=example",
    )


@pytest.fixture
def sample_digest(sample_game, sample_series, sample_recap, sample_headline) -> Digest:
    """Sample digest fixture."""
    return Digest(
        date="Thursday, April 25, 2026",
        round="First Round",
        main_headline="Hawks Stun Knicks in Playoff Game 3",
        sub_headline="Atlanta takes 2-1 series lead",
        games=[sample_game],
        active_series=[sample_series],
        recaps=[sample_recap],
        headlines=[sample_headline],
        standout_performances=[],
        plays_of_night_url="https://www.youtube.com/watch?v=playsofnight",
    )


@pytest.fixture
def sample_claude_response() -> str:
    """Sample Claude API response (raw JSON)."""
    return """{
        "date": "Thursday, April 25, 2026",
        "round": "First Round",
        "main_headline": "Hawks Stun Knicks in Playoff Game 3",
        "sub_headline": "Atlanta takes 2-1 series lead",
        "games": [{
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
        }],
        "active_series": [{
            "conference": "East",
            "top_seed": 4,
            "team1": "DET",
            "team1_wins": 1,
            "team2": "ORL",
            "team2_wins": 1
        }],
        "recaps": [{
            "title": "Hawks 107, Knicks 106 — Game 3",
            "body": "Atlanta stun New York..."
        }],
        "headlines": [{
            "bold_lead": "Hawks stun Knicks",
            "body": "Atlanta takes series lead"
        }],
        "standout_performances": [],
        "plays_of_night_url": "https://www.youtube.com/watch?v=example"
    }"""
