"""
Stage B: Validation and Preparation Module
Validates schemas, identifies duplicates, normalizes dates and ratings,
and maintains clear separation between raw evidence and cleaned records.
"""

import re
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class ReviewValidator:
    REQUIRED_FIELDS = ["score", "at"]

    @staticmethod
    def generate_fallback_id(content: str, user_name: str, date_str: str) -> str:
        """Fallback deterministic identifier if reviewId is absent."""
        seed = f"{user_name}|{date_str}|{content}".strip().lower()
        return "gen_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def clean_text(cls, text: Optional[str]) -> str:
        if not text:
            return ""
        text = str(text).strip()
        # Collapse excessive newlines and whitespace
        text = re.sub(r"\s+", " ", text)
        return text

    @classmethod
    def parse_datetime(cls, val: Any) -> Optional[datetime]:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        val_str = str(val).strip()
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%b %d, %Y"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(val_str[:19], fmt)
            except ValueError:
                continue
        # ISO parse fallback
        try:
            return pd.to_datetime(val_str).to_pydatetime()
        except Exception:
            return None

    @classmethod
    def validate_and_normalize(cls, raw_reviews: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validates raw reviews, removes internal duplicates, normalizes fields.
        Returns (cleaned_reviews, validation_report).
        """
        seen_ids = set()
        cleaned_records = []
        invalid_count = 0
        missing_content_count = 0
        missing_version_count = 0
        duplicate_count = 0

        for item in raw_reviews:
            # 1. Rating validation
            try:
                score = int(item.get("score", 0))
                if score < 1 or score > 5:
                    invalid_count += 1
                    continue
            except (ValueError, TypeError):
                invalid_count += 1
                continue

            # 2. Date parsing
            dt = cls.parse_datetime(item.get("at"))
            if dt is None:
                invalid_count += 1
                continue

            date_str = dt.strftime("%Y-%m-%d")
            period_str = dt.strftime("%Y-%m")

            # 3. Content cleaning
            raw_content = item.get("content")
            clean_content = cls.clean_text(raw_content)
            if not clean_content:
                missing_content_count += 1

            # 4. Identifier handling
            review_id = item.get("reviewId")
            if not review_id or str(review_id).strip() == "":
                review_id = cls.generate_fallback_id(clean_content, str(item.get("userName", "")), date_str)
            else:
                review_id = str(review_id).strip()

            if review_id in seen_ids:
                duplicate_count += 1
                continue
            seen_ids.add(review_id)

            # 5. Version handling
            ver = item.get("reviewCreatedVersion") or item.get("appVersion")
            if not ver or str(ver).lower() in ["nan", "none", ""]:
                ver = "Unknown"
                missing_version_count += 1
            else:
                ver = str(ver).strip()

            cleaned_records.append({
                "review_id": review_id,
                "app_id": item.get("app_id", "com.moveinsync.ets"),
                "cleaned_content": clean_content,
                "score": score,
                "review_date": date_str,
                "reporting_period": period_str,
                "app_version": ver,
                "thumbs_up_count": int(item.get("thumbsUpCount", 0)),
                "has_developer_reply": 1 if item.get("replyContent") else 0,
                "is_critical": 1 if score <= 2 else 0,
                "dt_obj": dt
            })

        validation_report = {
            "total_input_records": len(raw_reviews),
            "valid_unique_records": len(cleaned_records),
            "duplicate_records_filtered": duplicate_count,
            "invalid_records_rejected": invalid_count,
            "missing_content_count": missing_content_count,
            "missing_version_count": missing_version_count,
            "date_range_start": min(r["review_date"] for r in cleaned_records) if cleaned_records else None,
            "date_range_end": max(r["review_date"] for r in cleaned_records) if cleaned_records else None,
        }

        logger.info(
            "Validation finished: %d valid records, %d duplicates filtered, %d rejected.",
            validation_report["valid_unique_records"],
            validation_report["duplicate_records_filtered"],
            validation_report["invalid_records_rejected"]
        )

        return cleaned_records, validation_report
