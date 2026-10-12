"""
Stage A: Evidence Collection Module
Collects legitimate public Google Play Store reviews and app metadata for MoveInSync (com.moveinsync.ets).
Supports live fetching, rate limiting, and structured JSON/CSV fallback importing.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import pandas as pd

try:
    from google_play_scraper import app as fetch_app, reviews as fetch_reviews, Sort
    SCRAPER_AVAILABLE = True
except ImportError:
    SCRAPER_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

OFFICIAL_APP_ID = "com.moveinsync.ets"
RAW_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")


class MoveInSyncCollector:
    def __init__(self, app_id: str = OFFICIAL_APP_ID, raw_dir: str = RAW_DATA_DIR):
        self.app_id = app_id
        self.raw_dir = raw_dir
        os.makedirs(self.raw_dir, exist_ok=True)

    def get_app_metadata(self) -> Dict[str, Any]:
        """Fetches live public app metadata from Google Play Store."""
        if not SCRAPER_AVAILABLE:
            raise RuntimeError("google-play-scraper is not installed.")

        try:
            info = fetch_app(self.app_id, lang="en", country="in")
            metadata = {
                "app_id": self.app_id,
                "title": info.get("title", "MoveInSync"),
                "developer": info.get("developer", "MoveInSync: Enabling Hybrid Workplaces"),
                "score": float(info.get("score", 0.0)),
                "ratings": int(info.get("ratings", 0)),
                "reviews": int(info.get("reviews", 0)),
                "histogram": info.get("histogram", [0, 0, 0, 0, 0]),
                "installs": str(info.get("installs", "1,000,000+")),
                "genre": str(info.get("genre", "Maps & Navigation")),
                "version": str(info.get("version", "12.19.0")),
                "updated_timestamp": info.get("updated"),
                "source": "Google Play Store (India)",
                "collected_at": datetime.utcnow().isoformat()
            }
            # Snapshot metadata
            snapshot_path = os.path.join(self.raw_dir, f"app_metadata_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
            logger.info("Successfully fetched live metadata for %s. Displayed Score: %s", self.app_id, metadata['score'])
            return metadata
        except Exception as e:
            logger.error("Failed to fetch live app metadata: %s", str(e))
            raise

    def fetch_live_reviews(self, count: int = 3000) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Fetches live reviews sorted by NEWEST.
        Returns (list_of_reviews, metadata).
        """
        if not SCRAPER_AVAILABLE:
            raise RuntimeError("google-play-scraper is not installed.")

        metadata = self.get_app_metadata()
        logger.info("Collecting up to %d reviews for %s...", count, self.app_id)
        
        raw_items, _ = fetch_reviews(
            self.app_id,
            lang="en",
            country="in",
            sort=Sort.NEWEST,
            count=count
        )
        
        logger.info("Retrieved %d raw review records from Google Play.", len(raw_items))
        
        # Save raw snapshot
        timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        snapshot_filename = f"reviews_raw_live_{timestamp_str}.json"
        snapshot_path = os.path.join(self.raw_dir, snapshot_filename)
        
        serializable_items = []
        for item in raw_items:
            item_copy = dict(item)
            if isinstance(item_copy.get('at'), datetime):
                item_copy['at'] = item_copy['at'].isoformat()
            if isinstance(item_copy.get('repliedAt'), datetime):
                item_copy['repliedAt'] = item_copy['repliedAt'].isoformat()
            serializable_items.append(item_copy)

        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump({
                "source": "Google Play Store (live)",
                "app_id": self.app_id,
                "collection_timestamp": datetime.utcnow().isoformat(),
                "review_count": len(serializable_items),
                "reviews": serializable_items
            }, f, indent=2)

        return raw_items, metadata

    def import_from_file(self, filepath: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Usable import workflow for legitimate public evidence when direct collection is offline.
        Supports JSON or CSV.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Import file does not exist: {filepath}")

        logger.info("Importing public evidence from file: %s", filepath)
        if filepath.endswith(".json"):
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "reviews" in data:
                reviews = data["reviews"]
                metadata = data.get("metadata", {
                    "app_id": self.app_id,
                    "title": "MoveInSync (Imported)",
                    "score": 4.64,
                    "collected_at": datetime.utcnow().isoformat()
                })
            elif isinstance(data, list):
                reviews = data
                metadata = {"app_id": self.app_id, "score": 4.64, "collected_at": datetime.utcnow().isoformat()}
            else:
                raise ValueError("Unrecognized JSON format for reviews import.")
        elif filepath.endswith(".csv"):
            df = pd.read_csv(filepath)
            reviews = df.to_dict(orient="records")
            metadata = {"app_id": self.app_id, "score": 4.64, "collected_at": datetime.utcnow().isoformat()}
        else:
            raise ValueError("Supported file formats are .json and .csv")

        logger.info("Imported %d reviews from %s", len(reviews), filepath)
        return reviews, metadata
