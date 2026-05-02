"""Data models for NBA Digest with Pydantic validation."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
import json
import re


class Game(BaseModel):
    """A single playoff game result."""

    winner_abbr: str = Field(..., description="Winning team abbreviation (e.g. ATL)")
    winner_name: str = Field(..., description="Winning team name (e.g. Hawks)")
    winner_score: int = Field(..., ge=0, description="Winning team score")
    loser_abbr: str = Field(..., description="Losing team abbreviation (e.g. NYK)")
    loser_name: str = Field(..., description="Losing team name (e.g. Knicks)")
    loser_score: int = Field(..., ge=0, description="Losing team score")
    game_number: int = Field(..., ge=1, le=7, description="Game number in series (1-7)")
    venue: str = Field(..., description="Game venue/location")
    series_status: str = Field(..., description="Series status (e.g. ATL leads 2-1)")
    pts_leader: str = Field(..., description="Points leader (e.g. McCollum 23)")
    reb_leader: str = Field(..., description="Rebounds leader (e.g. Johnson 10)")
    ast_leader: str = Field(..., description="Assists leader (e.g. Barnes 11)")

    @field_validator('winner_score', 'loser_score')
    @classmethod
    def scores_non_negative(cls, v: int) -> int:
        """Validate scores are non-negative."""
        if v < 0:
            raise ValueError("Score must be non-negative")
        return v

    @field_validator('game_number')
    @classmethod
    def valid_game_number(cls, v: int) -> int:
        """Validate game number is 1-7."""
        if not 1 <= v <= 7:
            raise ValueError("Game number must be 1-7")
        return v


class ActiveSeries(BaseModel):
    """A current playoff series with standings."""

    conference: str = Field(..., description="East or West")
    top_seed: int = Field(..., ge=1, le=8, description="Higher seed number in matchup")
    team1: str = Field(..., description="First team abbreviation")
    team1_wins: int = Field(default=0, ge=0, le=4, description="First team wins (0-4)")
    team2: str = Field(..., description="Second team abbreviation")
    team2_wins: int = Field(default=0, ge=0, le=4, description="Second team wins (0-4)")

    @field_validator('conference')
    @classmethod
    def valid_conference(cls, v: str) -> str:
        """Validate conference is East or West."""
        if v not in ("East", "West"):
            raise ValueError("Conference must be 'East' or 'West'")
        return v

    @field_validator('team1_wins', 'team2_wins')
    @classmethod
    def valid_wins(cls, v: int) -> int:
        """Validate wins are 0-4."""
        if not 0 <= v <= 4:
            raise ValueError("Wins must be 0-4")
        return v


class StandoutPerformance(BaseModel):
    """A player's standout performance in a game."""

    name: str = Field(..., description="Player name")
    context: str = Field(..., description="Game context (e.g. in Game 3 win vs. Suns)")
    stats: str = Field(..., description="Stats string (e.g. 42 pts · 8 ast)")
    note: str = Field(..., description="Brief analysis/note")
    player_id: str = Field(..., description="NBA.com player ID (used for headshots)")
    highlight_url: Optional[str] = Field(default=None, description="YouTube highlight link")


class Recap(BaseModel):
    """A game recap/narrative."""

    title: str = Field(..., description="Game title (e.g. Hawks 107, Knicks 106 — Game 3)")
    body: str = Field(..., description="Narrative recap (2-6 sentences)")


class Headline(BaseModel):
    """A news headline or talking point."""

    bold_lead: str = Field(..., description="Bold intro sentence")
    body: str = Field(..., description="1-2 sentence explanation")


class Digest(BaseModel):
    """Complete NBA digest for a single day."""

    date: str = Field(..., description="Formatted date (e.g. Thursday, April 25, 2026)")
    round: str = Field(..., description="Playoff round (e.g. First Round, Conference Finals)")
    main_headline: str = Field(..., description="Main headline about the night's games")
    sub_headline: str = Field(default="", description="Secondary headline/context")
    games: List[Game] = Field(default_factory=list, description="Games played")
    active_series: List[ActiveSeries] = Field(default_factory=list, description="All playoff series")
    recaps: List[Recap] = Field(default_factory=list, description="Game recaps")
    headlines: List[Headline] = Field(default_factory=list, description="News items")
    standout_performances: List[StandoutPerformance] = Field(
        default_factory=list, description="Best individual performances"
    )
    plays_of_night_url: Optional[str] = Field(default=None, description="NBA Plays of Night YouTube link")

    @classmethod
    def from_claude_response(cls, raw_text: str) -> "Digest":
        """
        Parse and validate Claude's JSON response.

        Handles markdown code fences, narration before/after JSON, etc.

        Args:
            raw_text: Raw text from Claude API response

        Returns:
            Digest: Validated Digest model

        Raises:
            ValueError: If JSON cannot be extracted or validated
        """
        # Remove markdown code fences
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()

        # Try markdown code fences first
        match = re.search(r"```(?:json)?\s*\n(.*?)\n```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1)

        # Try raw JSON object
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON object found in Claude response")

        json_str = cleaned[start:end]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse Claude response as JSON: {e}")

        try:
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Failed to validate digest data: {e}")

    def dict(self, **kwargs) -> dict:
        """Convert to dictionary (compatible with json.dumps)."""
        return super().model_dump(**kwargs)

    def json(self, **kwargs) -> str:
        """Convert to JSON string."""
        return super().model_dump_json(**kwargs)
