"""Tests for API clients."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from nba_digest.api.reddit import RedditClient
from nba_digest.api.espn import ESPNClient
from nba_digest.api.claude import ClaudeClient


class TestRedditClient:
    """Test Reddit API client."""

    @patch("urllib.request.urlopen")
    def test_fetch_posts_success(self, mock_urlopen):
        """Successful Reddit fetch returns formatted string."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"""{
            "data": {
                "children": [
                    {"data": {"title": "Test Post", "score": 100, "num_comments": 50, "stickied": false}}
                ]
            }
        }"""
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = RedditClient()
        posts = client.fetch_posts()

        assert isinstance(posts, str)
        assert "Test Post" in posts
        assert "100 pts" in posts

    @patch("urllib.request.urlopen")
    def test_fetch_posts_failure(self, mock_urlopen):
        """Reddit fetch failure returns empty string (non-fatal)."""
        mock_urlopen.side_effect = Exception("Connection error")

        client = RedditClient()
        posts = client.fetch_posts()

        assert posts == ""

    @patch("urllib.request.urlopen")
    def test_fetch_posts_filters_stickied(self, mock_urlopen):
        """Stickied posts are filtered out."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"""{
            "data": {
                "children": [
                    {"data": {"title": "Sticky", "stickied": true}},
                    {"data": {"title": "Normal", "score": 10, "num_comments": 5, "stickied": false}}
                ]
            }
        }"""
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = RedditClient()
        posts = client.fetch_posts()

        assert "Sticky" not in posts
        assert "Normal" in posts


class TestClaudeClient:
    """Test Claude API client."""

    @patch("anthropic.Anthropic")
    def test_generate_digest_success(self, mock_anthropic_class, sample_claude_response):
        """Successful Claude call returns parsed Digest."""
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text=sample_claude_response)]
        mock_client.messages.create.return_value = mock_response

        # Test
        claude = ClaudeClient(api_key="test-key")
        digest = claude.generate_digest("Test prompt")

        assert digest.main_headline == "Hawks Stun Knicks in Playoff Game 3"
        assert len(digest.games) == 1

    @patch("anthropic.Anthropic")
    def test_generate_digest_retry_on_json_error(self, mock_anthropic_class):
        """JSON parse error triggers retry."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        # First call: invalid JSON, Second call: valid JSON
        invalid_response = MagicMock()
        invalid_response.content = [MagicMock(type="text", text="Not JSON")]

        valid_json = """{
            "date": "Test",
            "round": "Test",
            "main_headline": "Test",
            "sub_headline": "Test",
            "games": [],
            "active_series": [],
            "recaps": [],
            "headlines": [],
            "standout_performances": []
        }"""
        valid_response = MagicMock()
        valid_response.content = [MagicMock(type="text", text=valid_json)]

        mock_client.messages.create.side_effect = [invalid_response, valid_response]

        # Test with short backoff for testing
        claude = ClaudeClient(api_key="test-key", json_parse_backoff=0)

        with patch("time.sleep"):  # Don't actually sleep in tests
            digest = claude.generate_digest("Test prompt")

        assert digest.main_headline == "Test"


class TestESPNClient:
    """Test ESPN API client."""

    @patch("urllib.request.urlopen")
    def test_fetch_series_success(self, mock_urlopen):
        """Successful ESPN fetch returns series list."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"""{
            "events": [{
                "competitions": [{
                    "series": {"competitors": [
                        {"id": "1", "wins": 2},
                        {"id": "2", "wins": 1}
                    ]},
                    "competitors": [
                        {"team": {"id": "1", "abbreviation": "ATL", "color": "E03828"}},
                        {"team": {"id": "2", "abbreviation": "NYK", "color": "0E2340"}}
                    ]
                }]
            }]
        }"""
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        client = ESPNClient()
        series_list = client.fetch_series()

        assert len(series_list) > 0

    @patch("urllib.request.urlopen")
    def test_fetch_series_failure(self, mock_urlopen):
        """ESPN fetch failure returns empty list."""
        mock_urlopen.side_effect = Exception("Connection error")

        client = ESPNClient()
        series_list = client.fetch_series()

        assert series_list == []
