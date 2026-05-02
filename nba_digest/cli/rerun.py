#!/usr/bin/env python3
"""CLI for re-running digest generation for a specific date."""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from nba_digest.config import Config
from nba_digest.services.digest import DigestService
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
    Re-run digest generation for a specific date (without sending email).

    Usage: python -m nba_digest.cli.rerun [YYYY-MM-DD]
    Default: yesterday's date

    This is useful for:
    - Generating digests for dates that were missed
    - Regenerating a digest with updated data
    - Testing digest generation for a specific date

    Flow:
    1. Parse date argument (or default to yesterday)
    2. Load config from environment
    3. Generate digest for that date (time-machine via prompt)
    4. Build email and page HTML
    5. Save to cache and docs
    6. Update index
    """
    try:
        # Parse date argument
        if len(sys.argv) > 1:
            target_date_str = sys.argv[1]
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
            except ValueError:
                log.error(f"Invalid date format: {target_date_str}. Use YYYY-MM-DD")
                sys.exit(1)
        else:
            # Default to yesterday
            target_date = datetime.now() - timedelta(days=1)

        iso_date = target_date.strftime("%Y-%m-%d")
        date_short = target_date.strftime("%A, %B %-d")

        log.info(f"Generating digest for {iso_date} ({date_short})...")

        # Load config
        config = Config.from_env()

        # Generate digest
        digest_svc = DigestService(config)
        digest = digest_svc.generate()

        if not digest:
            log.error("Failed to generate digest")
            sys.exit(1)

        log.info(f"✓ Generated digest with {len(digest.games)} games")

        # Save cache and build pages
        storage = StorageService(config.cache_dir, config.docs_dir)
        storage.cache_digest(digest, iso_date)
        log.info(f"✓ Cached digest: cache/digest-{iso_date}.json")

        # Build and save email HTML
        email_builder = EmailBuilder()
        html_body = email_builder.build(digest, iso_date=iso_date)

        # Build and save page with navigation
        page_builder = PageBuilder()
        page_html = page_builder.build(digest, html_body, iso_date)
        storage.save_page(page_html, iso_date)
        log.info(f"✓ Saved page: docs/{iso_date}.html")

        # Update index
        index_builder = IndexBuilder(config.cache_dir, config.docs_dir)
        index_html = index_builder.build()
        storage.save_index(index_html)
        log.info(f"✓ Updated index: docs/index.html")

        log.info("=" * 60)
        log.info("SUCCESS: Re-run completed successfully")
        log.info("=" * 60)

    except Exception as e:
        log.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
