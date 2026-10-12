"""
Unit tests for MonthOverMonthComparator.
"""

import pytest
from analysis.mom_comparison import MonthOverMonthComparator


def test_mom_comparison_deltas():
    curr_run = {"reporting_period": "2026-10", "period_review_count": 100, "sample_rating": 3.80, "critical_review_count": 30}
    prev_run = {"reporting_period": "2026-09", "period_review_count": 80, "sample_rating": 3.60, "critical_review_count": 28}

    curr_issues = [{"theme_code": "LIVE_TRACKING_GPS", "theme_name": "Live Tracking", "prevalence_pct": 20.0, "critical_count": 6, "priority_rank": 1}]
    prev_issues = [{"theme_code": "LIVE_TRACKING_GPS", "theme_name": "Live Tracking", "prevalence_pct": 25.0, "critical_count": 7, "priority_rank": 1}]

    res = MonthOverMonthComparator.compare_monthly_runs(
        current_run=curr_run,
        previous_run=prev_run,
        current_reviews=[{"app_version": "12.19.0", "score": 1, "primary_theme": "LIVE_TRACKING_GPS"}] * 10,
        previous_reviews=[{"app_version": "12.18.0", "score": 1, "primary_theme": "LIVE_TRACKING_GPS"}] * 10,
        current_issues=curr_issues,
        previous_issues=prev_issues
    )

    assert res["has_previous_period"] is True
    assert res["volume"]["delta"] == 20
    assert res["rating"]["delta"] == 0.20
    assert len(res["theme_trajectories"]) == 1
    # 20.0 - 25.0 = -5.0 delta -> Improving status
    assert res["theme_trajectories"][0]["status"] == "Improving"


def test_mom_missing_previous_period():
    curr_run = {"reporting_period": "2025-09", "period_review_count": 50, "sample_rating": 3.70, "critical_review_count": 15}
    res = MonthOverMonthComparator.compare_monthly_runs(
        current_run=curr_run,
        previous_run=None,
        current_reviews=[],
        previous_reviews=None,
        current_issues=[],
        previous_issues=None
    )
    assert res["has_previous_period"] is False
    assert "Initial baseline" in res["summary"]
