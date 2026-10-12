"""
Unit tests for PrioritizationEngine scoring formulas and ranking comparisons.
"""

import pytest
from analysis.prioritization import PrioritizationEngine


def test_prioritization_scoring_logic():
    reviews = [
        {"review_id": "r1", "score": 1, "primary_theme": "LIVE_TRACKING_GPS"},
        {"review_id": "r2", "score": 1, "primary_theme": "LIVE_TRACKING_GPS"},
        {"review_id": "r3", "score": 1, "primary_theme": "FORCED_RATING_MODAL"},
        {"review_id": "r4", "score": 5, "primary_theme": "POSITIVE_EXPERIENCE"},
    ]
    issues = PrioritizationEngine.score_issues(reviews, "2026-10")

    assert len(issues) >= 2
    # Check that highest score gets rank 1
    assert issues[0]["priority_rank"] == 1
    assert issues[0]["priority_score"] >= issues[1]["priority_score"]


def test_prioritization_rank_comparison():
    curr = [
        {"theme_code": "LIVE_TRACKING_GPS", "priority_rank": 1, "priority_score": 7.5},
        {"theme_code": "FORCED_RATING_MODAL", "priority_rank": 2, "priority_score": 6.0},
    ]
    prev = [
        {"theme_code": "FORCED_RATING_MODAL", "priority_rank": 1, "priority_score": 7.0},
        {"theme_code": "LIVE_TRACKING_GPS", "priority_rank": 2, "priority_score": 6.8},
    ]

    compared = PrioritizationEngine.compare_rankings(curr, prev)
    tracking = next(x for x in compared if x["theme_code"] == "LIVE_TRACKING_GPS")
    # Previous was 2, now 1 -> rank_delta = 2 - 1 = +1
    assert tracking["rank_delta"] == 1
    assert tracking["prev_rank"] == 2
