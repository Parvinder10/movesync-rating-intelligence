"""
Unit and integration tests for ReviewValidator.
"""

import pytest
from datetime import datetime
from analysis.validator import ReviewValidator


def test_validator_clean_text():
    raw = "  Worst app!   \n\n It logged me out.  "
    cleaned = ReviewValidator.clean_text(raw)
    assert cleaned == "Worst app! It logged me out."


def test_validator_parse_datetime():
    dt1 = ReviewValidator.parse_datetime("2026-10-11 11:45:45")
    assert dt1 is not None
    assert dt1.year == 2026 and dt1.month == 10 and dt1.day == 11

    dt2 = ReviewValidator.parse_datetime("2026-08-15T09:30:00")
    assert dt2 is not None
    assert dt2.month == 8


def test_validator_deduplication():
    raw_sample = [
        {"reviewId": "rev_001", "score": 1, "at": "2026-10-01 10:00:00", "content": "Crash on launch", "reviewCreatedVersion": "12.19.0"},
        {"reviewId": "rev_001", "score": 1, "at": "2026-10-01 10:00:00", "content": "Crash on launch", "reviewCreatedVersion": "12.19.0"}, # Duplicate
        {"reviewId": "rev_002", "score": 5, "at": "2026-10-02 12:00:00", "content": "Great experience", "reviewCreatedVersion": "12.19.0"},
        {"reviewId": "rev_003", "score": 99, "at": "2026-10-03 14:00:00", "content": "Invalid score"}, # Invalid score
    ]
    cleaned, report = ReviewValidator.validate_and_normalize(raw_sample)

    assert len(cleaned) == 2
    assert report["total_input_records"] == 4
    assert report["valid_unique_records"] == 2
    assert report["duplicate_records_filtered"] == 1
    assert report["invalid_records_rejected"] == 1
    assert cleaned[0]["review_id"] == "rev_001"
    assert cleaned[1]["review_id"] == "rev_002"


def test_validator_fallback_id():
    fid1 = ReviewValidator.generate_fallback_id("bad app", "John", "2026-10-01")
    fid2 = ReviewValidator.generate_fallback_id("bad app", "John", "2026-10-01")
    assert fid1 == fid2
    assert fid1.startswith("gen_")
