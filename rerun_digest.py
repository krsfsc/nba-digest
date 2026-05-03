#!/usr/bin/env python3
"""
Standalone script to re-run digest generation for a specific date without sending email.
Usage: python3 rerun_digest.py [YYYY-MM-DD]
Default: yesterday's date
"""
import sys
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

# Import after path setup
from nba_digest.config import Config
from nba_digest.services.digest import DigestService
from nba_digest.services.storage import StorageService
from nba_digest.builders.email import EmailBuilder
from nba_digest.builders.page import PageBuilder

# Use the original build_index_html function which has full standings/games
# (IndexBuilder is still being completed)
import nba_digest

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

def main():
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

    try:
        # Load config from environment
        config = Config.from_env()

        # Generate digest using new service
        digest_svc = DigestService(config)
        digest = digest_svc.generate()

        if not digest:
            log.error("Failed to generate digest")
            sys.exit(1)

        log.info(f"Generated digest with {len(digest.games)} games")

        # Save cache and build pages
        storage = StorageService(config.cache_dir, config.docs_dir)
        storage.cache_digest(digest, iso_date)

        # Build and save email HTML
        email_builder = EmailBuilder()
        html_body = email_builder.build(digest, iso_date=iso_date)

        # Build and save page with navigation
        page_builder = PageBuilder()
        page_html = page_builder.build(digest, html_body, iso_date)
        storage.save_page(page_html, iso_date)

        # Update index using original build_index_html function
        # (preserves playoff standings, hero section, tonight's games)
        index_html = nba_digest.build_index_html()
        storage.save_index(index_html)

        log.info("Done! Re-run completed successfully.")
        log.info(f"Files saved:")
        log.info(f"  Cache: cache/digest-{iso_date}.json")
        log.info(f"  Page:  docs/{iso_date}.html")
        log.info(f"  Index: docs/index.html")

    except Exception as e:
        log.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
