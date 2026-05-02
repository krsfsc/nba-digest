#!/usr/bin/env python3
"""Main CLI entry point for digest generation and email sending."""

import logging
import sys
from datetime import datetime
from pathlib import Path

from nba_digest.config import Config
from nba_digest.services.digest import DigestService
from nba_digest.services.email import EmailService
from nba_digest.services.storage import StorageService
from nba_digest.builders.email import EmailBuilder
from nba_digest.builders.page import PageBuilder
from nba_digest.builders.index import IndexBuilder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)


def main() -> None:
    """
    Main entry point: Generate NBA digest, send email, and update archive.

    Flow:
    1. Load config from environment
    2. Generate digest (Reddit + Claude API)
    3. Build email HTML
    4. Build archive page HTML
    5. Send email to subscriber
    6. Save to cache and docs
    7. Update index
    """
    try:
        # Load configuration
        config = Config.from_env()
        log.info("Configuration loaded")

        # Generate digest
        log.info("Generating NBA digest...")
        digest_svc = DigestService(config)
        digest = digest_svc.generate()

        if not digest:
            log.error("Failed to generate digest (returned None)")
            sys.exit(1)

        log.info(f"✓ Digest generated with {len(digest.games)} games")

        # Get today's ISO date
        iso_date = datetime.now().strftime("%Y-%m-%d")

        # Build email HTML
        log.info("Building email HTML...")
        email_builder = EmailBuilder()
        html_body = email_builder.build(digest, iso_date=iso_date)
        log.info("✓ Email HTML built")

        # Build archive page
        log.info("Building archive page...")
        page_builder = PageBuilder()
        page_html = page_builder.build(digest, html_body, iso_date)
        log.info("✓ Archive page built")

        # Save to storage (cache and docs)
        log.info("Saving to cache and docs...")
        storage = StorageService(config.cache_dir, config.docs_dir)
        storage.cache_digest(digest, iso_date)
        storage.save_page(page_html, iso_date)
        log.info("✓ Files saved to cache and docs")

        # Update index
        log.info("Updating index...")
        index_builder = IndexBuilder(config.cache_dir, config.docs_dir)
        index_html = index_builder.build()
        storage.save_index(index_html)
        log.info("✓ Index updated")

        # Send email
        log.info("Sending email to subscriber...")
        email_svc = EmailService(config.sender_email, config.gmail_app_password)
        email_svc.send(
            to_email=config.recipient_email,
            subject=f"NBA Digest — {digest.main_headline}",
            html_body=html_body,
            text_body=f"NBA Digest for {digest.date}\n{digest.main_headline}"
        )
        log.info(f"✓ Email sent to {config.recipient_email}")

        log.info("=" * 60)
        log.info("SUCCESS: Digest generated, saved, and emailed")
        log.info("=" * 60)

    except KeyboardInterrupt:
        log.error("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        log.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
