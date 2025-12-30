import json
import logging
import os
from typing import Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class RateMyProfService:
    """
    Local RMP Service - Reads from scraped JSON database.
    """

    def __init__(self, db_file: str = "rmp_data.json", api_key: str = None):
        # We accept api_key for backward compatibility but don't use it
        self.db_file = db_file
        self.professors = {}
        self._load_database()

    def _load_database(self):
        """Load the JSON database into memory."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r') as f:
                    self.professors = json.load(f)
                logger.info(f"✅ RMP Service: Loaded {len(self.professors)} professors from local DB.")
            except Exception as e:
                logger.error(f"❌ Failed to load RMP database: {e}")
        else:
            logger.warning(f"⚠️  RMP database file '{self.db_file}' not found. Run rmp_scraper.py first.")

    def get_professor_difficulty(self, professor_name: str) -> Dict:
        """Get difficulty stats for a specific professor."""
        if not professor_name:
            return {"difficulty": 3.0, "found": False}

        prof_data = self.professors.get(professor_name)

        if prof_data and prof_data.get("found") is not False:
            return {
                "difficulty": prof_data.get("avgDifficulty", 3.0),
                "rating": prof_data.get("avgRating", 3.0),
                "num_ratings": prof_data.get("numRatings", 0),
                "found": True
            }
        
        return {"difficulty": 3.0, "found": False}

    def _load_cached_professors(self):
        """Return all data (for frontend API)."""
        return self.professors