"""Configuration management with environment variable validation."""

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Optional


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # Required
    anthropic_api_key: str
    gmail_app_password: str

    # Email
    sender_email: str
    recipient_email: str = "rentapolo@gmail.com"

    # Paths
    cache_dir: Path = field(default_factory=lambda: Path("cache"))
    docs_dir: Path = field(default_factory=lambda: Path("docs"))

    # API behavior
    max_retries: int = 3
    rate_limit_backoff_seconds: int = 180
    json_parse_backoff_seconds: int = 90
    max_output_tokens: int = 2000

    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables with validation.

        Required environment variables:
            ANTHROPIC_API_KEY: Claude API key
            GMAIL_APP_PASSWORD: Gmail app-specific password

        Optional environment variables:
            SENDER_EMAIL: Gmail address to send from
            DIGEST_EMAIL: Email to send digest to
            DIGEST_CACHE_DIR: Directory for cached digests
            DOCS_DIR: Directory for generated HTML pages

        Returns:
            Config: Validated configuration object

        Raises:
            ValueError: If required environment variables are missing
        """
        # Validate required fields
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable must be set. "
                "Get it from https://console.anthropic.com"
            )

        gmail_pwd = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
        if not gmail_pwd:
            raise ValueError(
                "GMAIL_APP_PASSWORD environment variable must be set. "
                "Create an app password at https://myaccount.google.com/apppasswords"
            )

        # Optional fields with defaults
        digest_email = os.environ.get("DIGEST_EMAIL", "").strip()
        sender_email = os.environ.get("SENDER_EMAIL", "").strip()

        if not sender_email:
            sender_email = digest_email if digest_email else "rentapolo@gmail.com"
        if not digest_email:
            digest_email = "rentapolo@gmail.com"

        cache_dir = Path(os.environ.get("DIGEST_CACHE_DIR", "cache"))
        docs_dir = Path(os.environ.get("DOCS_DIR", "docs"))

        return cls(
            anthropic_api_key=api_key,
            gmail_app_password=gmail_pwd,
            sender_email=sender_email,
            recipient_email=digest_email,
            cache_dir=cache_dir,
            docs_dir=docs_dir,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Load configuration from a dictionary."""
        return cls(**data)

    def validate(self) -> None:
        """Validate all configuration values."""
        if not self.anthropic_api_key:
            raise ValueError("anthropic_api_key cannot be empty")
        if not self.gmail_app_password:
            raise ValueError("gmail_app_password cannot be empty")
        if not self.sender_email:
            raise ValueError("sender_email cannot be empty")
        if not self.recipient_email:
            raise ValueError("recipient_email cannot be empty")
        if self.max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        if self.rate_limit_backoff_seconds < 1:
            raise ValueError("rate_limit_backoff_seconds must be at least 1")
        if self.max_output_tokens < 100:
            raise ValueError("max_output_tokens must be at least 100")
