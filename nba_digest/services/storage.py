"""File storage service for caching and persistence."""

import json
import logging
from pathlib import Path
from typing import Dict, Any

from nba_digest.models import Digest

log = logging.getLogger(__name__)


class StorageService:
    """Handles file I/O for digest caching and page generation."""

    def __init__(self, cache_dir: Path, docs_dir: Path):
        """
        Initialize storage service.

        Args:
            cache_dir: Directory for cached JSON digests
            docs_dir: Directory for generated HTML pages
        """
        self.cache_dir = Path(cache_dir)
        self.docs_dir = Path(docs_dir)

    def cache_digest(self, digest: Digest, iso_date: str) -> Path:
        """
        Cache digest as JSON.

        Args:
            digest: Digest model to cache
            iso_date: Date in YYYY-MM-DD format

        Returns:
            Path to cached file
        """
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"digest-{iso_date}.json"

        # Convert Pydantic model to JSON
        cache_file.write_text(json.dumps(digest.model_dump(), indent=2))
        log.info("Cached digest to %s", cache_file)

        return cache_file

    def save_page(self, html_content: str, iso_date: str) -> Path:
        """
        Save HTML page to docs directory.

        Args:
            html_content: HTML content to save
            iso_date: Date in YYYY-MM-DD format

        Returns:
            Path to saved file
        """
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        page_file = self.docs_dir / f"{iso_date}.html"

        page_file.write_text(html_content)
        log.info("Saved page to %s", page_file)

        return page_file

    def save_index(self, html_content: str) -> Path:
        """
        Save index.html to docs directory.

        Args:
            html_content: Index HTML content

        Returns:
            Path to saved file
        """
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        index_file = self.docs_dir / "index.html"

        index_file.write_text(html_content)
        log.info("Saved index to %s", index_file)

        return index_file

    def load_digest(self, iso_date: str) -> Digest:
        """
        Load cached digest.

        Args:
            iso_date: Date in YYYY-MM-DD format

        Returns:
            Loaded Digest model

        Raises:
            FileNotFoundError: If cache doesn't exist
            ValueError: If JSON is invalid
        """
        cache_file = self.cache_dir / f"digest-{iso_date}.json"

        if not cache_file.exists():
            raise FileNotFoundError(f"No cached digest for {iso_date}")

        try:
            data = json.loads(cache_file.read_text())
            return Digest(**data)
        except Exception as e:
            raise ValueError(f"Failed to load digest from {cache_file}: {e}")
