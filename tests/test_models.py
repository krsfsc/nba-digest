"""Tests for Pydantic models."""

import pytest
from nba_digest.models import Digest, Game, ActiveSeries, StandoutPerformance


class TestGame:
    """Test Game model validation."""

    def test_valid_game(self, sample_game):
        """Valid game data passes validation."""
        assert sample_game.winner_abbr == "ATL"
        assert sample_game.winner_score == 107

    def test_negative_score_fails(self):
        """Negative scores should fail validation."""
        with pytest.raises(ValueError):
            Game(
                winner_abbr="ATL",
                winner_name="Hawks",
                winner_score=-5,  # Invalid!
                loser_abbr="NYK",
                loser_name="Knicks",
                loser_score=100,
                game_number=1,
                venue="Stadium",
                series_status="ATL leads 1-0",
                pts_leader="Player 10",
                reb_leader="Player 5",
                ast_leader="Player 3",
            )

    def test_invalid_game_number(self):
        """Game number must be 1-7."""
        with pytest.raises(ValueError):
            Game(
                winner_abbr="ATL",
                winner_name="Hawks",
                winner_score=100,
                loser_abbr="NYK",
                loser_name="Knicks",
                loser_score=90,
                game_number=8,  # Invalid!
                venue="Stadium",
                series_status="ATL leads",
                pts_leader="P1 10",
                reb_leader="P2 5",
                ast_leader="P3 3",
            )


class TestActiveSeries:
    """Test ActiveSeries model validation."""

    def test_valid_series(self, sample_series):
        """Valid series passes validation."""
        assert sample_series.conference == "East"
        assert sample_series.top_seed == 4

    def test_invalid_conference(self):
        """Conference must be East or West."""
        with pytest.raises(ValueError):
            ActiveSeries(
                conference="Central",  # Invalid!
                top_seed=1,
                team1="ATL",
                team1_wins=1,
                team2="NYK",
                team2_wins=0,
            )

    def test_invalid_wins(self):
        """Wins must be 0-4."""
        with pytest.raises(ValueError):
            ActiveSeries(
                conference="East",
                top_seed=1,
                team1="ATL",
                team1_wins=5,  # Invalid! Must be 0-4
                team2="NYK",
                team2_wins=0,
            )


class TestDigest:
    """Test Digest model validation and parsing."""

    def test_valid_digest(self, sample_digest):
        """Valid digest passes validation."""
        assert sample_digest.main_headline == "Hawks Stun Knicks in Playoff Game 3"
        assert len(sample_digest.games) == 1

    def test_parse_from_claude_response(self, sample_claude_response):
        """Parse and validate Claude JSON response."""
        digest = Digest.from_claude_response(sample_claude_response)
        assert digest.main_headline == "Hawks Stun Knicks in Playoff Game 3"
        assert len(digest.games) == 1
        assert digest.games[0].winner_abbr == "ATL"

    def test_parse_with_markdown_fences(self):
        """Handle Claude response with markdown code fences."""
        response = """Here's the digest:

```json
{
    "date": "Thursday, April 25, 2026",
    "round": "First Round",
    "main_headline": "Test",
    "sub_headline": "Test",
    "games": [],
    "active_series": [],
    "recaps": [],
    "headlines": [],
    "standout_performances": []
}
```"""
        digest = Digest.from_claude_response(response)
        assert digest.main_headline == "Test"

    def test_parse_invalid_json(self):
        """Invalid JSON should raise ValueError."""
        with pytest.raises(ValueError):
            Digest.from_claude_response("This is not JSON at all")

    def test_missing_required_field(self):
        """Missing required field should fail validation."""
        invalid_json = """{
            "date": "Thursday, April 25, 2026",
            "round": "First Round"
        }"""
        with pytest.raises(ValueError):
            Digest.from_claude_response(invalid_json)

    def test_dict_conversion(self, sample_digest):
        """Digest should convert to dict."""
        d = sample_digest.dict()
        assert isinstance(d, dict)
        assert d["main_headline"] == sample_digest.main_headline

    def test_json_conversion(self, sample_digest):
        """Digest should convert to JSON string."""
        j = sample_digest.json()
        assert isinstance(j, str)
        assert "Hawks Stun Knicks" in j
