"""Claude API client for digest generation with retry logic."""

import logging
import time
from typing import Optional

import anthropic

from nba_digest.models import Digest
from nba_digest.config import Config

log = logging.getLogger(__name__)


class ClaudeClient:
    """Calls Claude API with web search and retry logic."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_retries: int = 3,
        rate_limit_backoff: int = 180,
        json_parse_backoff: int = 90,
        max_tokens: int = 6000,
    ):
        """
        Initialize Claude client.

        Args:
            api_key: Anthropic API key
            model: Model to use
            max_retries: Maximum retry attempts
            rate_limit_backoff: Seconds to wait on rate limit (429) errors
            json_parse_backoff: Seconds to wait on JSON parse errors (multiplied by attempt)
            max_tokens: Maximum output tokens
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_retries = max_retries
        self.rate_limit_backoff = rate_limit_backoff
        self.json_parse_backoff = json_parse_backoff
        self.max_tokens = max_tokens

    def generate_digest(self, prompt: str) -> Digest:
        """
        Generate NBA digest from a prompt using Claude with web search.

        Retries up to max_retries times with exponential backoff on failures.
        Validates response with Pydantic models.

        Args:
            prompt: Full prompt text for Claude

        Returns:
            Digest: Validated digest model

        Raises:
            RuntimeError: If all retry attempts fail
        """
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                log.info("Calling Claude API (attempt %d/%d)...", attempt, self.max_retries)

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    # Web search can cause mixed content (search results + JSON)
                    # Disable for cleaner JSON responses. Claude has knowledge cutoff
                    # and can generate digests without live search.
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract text blocks from response
                text_parts = []
                for block in response.content:
                    if block.type == "text" and block.text:
                        text_parts.append(block.text)

                raw = "\n".join(text_parts).strip()

                if not raw:
                    raise RuntimeError("Claude returned no text content")

                log.info("Received response, parsing JSON...")

                # Parse and validate response with Digest model
                digest = Digest.from_claude_response(raw)
                log.info("Digest generated with %d games", len(digest.games))

                return digest

            except (ValueError, RuntimeError) as e:
                # JSON parse error - wait and retry
                last_error = e
                log.warning(
                    "Attempt %d: JSON parse failed: %s",
                    attempt,
                    e,
                )
                if attempt < self.max_retries:
                    backoff = self.json_parse_backoff * attempt
                    log.info("Waiting %ds before retry...", backoff)
                    time.sleep(backoff)

            except Exception as e:
                # Other API errors (rate limit, timeout, etc)
                last_error = e

                # Check if rate limited
                is_rate_limited = (
                    "429" in str(e)
                    or "rate_limit" in str(e).lower()
                    or "too many requests" in str(e).lower()
                )

                if is_rate_limited:
                    log.warning(
                        "Attempt %d failed: Rate limited",
                        attempt,
                    )
                    backoff = self.rate_limit_backoff
                else:
                    log.warning(
                        "Attempt %d failed: %s",
                        attempt,
                        e,
                    )
                    backoff = 10 * attempt

                if attempt < self.max_retries:
                    log.info("Waiting %ds before retry...", backoff)
                    time.sleep(backoff)

        # All retries exhausted
        raise RuntimeError(
            f"Failed to generate digest after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    @classmethod
    def from_config(cls, config: Config) -> "ClaudeClient":
        """Create ClaudeClient from Config object."""
        return cls(
            api_key=config.anthropic_api_key,
            max_retries=config.max_retries,
            rate_limit_backoff=config.rate_limit_backoff_seconds,
            json_parse_backoff=config.json_parse_backoff_seconds,
            max_tokens=config.max_output_tokens,
        )
