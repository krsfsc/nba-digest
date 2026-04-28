#!/usr/bin/env python3
"""
Standalone script to re-run digest generation for a specific date without sending email.
Usage: python3 rerun_digest.py [YYYY-MM-DD]
Default: yesterday's date (April 26)
"""
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent)

# Import after path setup
from nba_digest import (
    generate_digest, 
    build_email_html, 
    build_plaintext,
    CACHE_DIR,
    DOCS_DIR,
    update_index,
)

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
        # Generate digest
        digest = generate_digest()
        
        if not digest:
            log.error("Failed to generate digest")
            sys.exit(1)
        
        log.info(f"Generated digest with {len(digest.get('games', []))} games")
        
        # Save cache JSON
        cache_file = CACHE_DIR / f"digest-{iso_date}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(digest, indent=2))
        log.info(f"Saved cache: {cache_file}")
        
        # Save HTML page
        html_body = build_email_html(digest, iso_date=iso_date)
        html_file = DOCS_DIR / f"{iso_date}.html"
        html_file.parent.mkdir(parents=True, exist_ok=True)
        html_file.write_text(html_body)
        log.info(f"Saved HTML: {html_file}")
        
        # Update index
        update_index()
        log.info("Updated index.html")
        
        log.info("Done! Re-run completed successfully.")
        log.info(f"Files saved:")
        log.info(f"  Cache: {cache_file}")
        log.info(f"  HTML:  {html_file}")
        
    except Exception as e:
        log.error(f"Failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
