"""
Stage E & H: Month-over-Month Comparison Engine
Calculates volume changes, rating shifts, theme trajectory (new, persistent, improving, worsening),
and version-specific breakdown across consecutive monthly runs.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np


class MonthOverMonthComparator:
    @classmethod
    def compare_monthly_runs(
        cls,
        current_run: Dict[str, Any],
        previous_run: Optional[Dict[str, Any]],
        current_reviews: List[Dict[str, Any]],
        previous_reviews: Optional[List[Dict[str, Any]]],
        current_issues: List[Dict[str, Any]],
        previous_issues: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Generates full MoM comparison report between two monthly periods.
        """
        curr_vol = current_run.get("period_review_count", len(current_reviews))
        curr_rating = current_run.get("sample_rating", 0.0)
        curr_critical = current_run.get("critical_review_count", 0)
        curr_critical_pct = round((curr_critical / curr_vol * 100), 1) if curr_vol > 0 else 0.0

        if not previous_run or not previous_reviews:
            return {
                "has_previous_period": False,
                "current_period": current_run.get("reporting_period"),
                "previous_period": None,
                "volume": {"current": curr_vol, "previous": None, "delta": None, "pct_change": None},
                "rating": {"current": curr_rating, "previous": None, "delta": None},
                "critical_pct": {"current": curr_critical_pct, "previous": None, "delta": None},
                "theme_trajectories": [],
                "version_patterns": cls.extract_version_patterns(current_reviews),
                "summary": "Initial baseline established. No preceding monthly snapshot available."
            }

        prev_vol = previous_run.get("period_review_count", len(previous_reviews))
        prev_rating = previous_run.get("sample_rating", 0.0)
        prev_critical = previous_run.get("critical_review_count", 0)
        prev_critical_pct = round((prev_critical / prev_vol * 100), 1) if prev_vol > 0 else 0.0

        vol_delta = curr_vol - prev_vol
        vol_pct = round((vol_delta / prev_vol * 100), 1) if prev_vol > 0 else 0.0
        rating_delta = round(curr_rating - prev_rating, 2)
        critical_pct_delta = round(curr_critical_pct - prev_critical_pct, 1)

        # Theme trajectories
        prev_issue_map = {item["theme_code"]: item for item in (previous_issues or [])}
        trajectories = []

        all_theme_codes = set([item["theme_code"] for item in current_issues] + list(prev_issue_map.keys()))

        for code in all_theme_codes:
            curr_item = next((x for x in current_issues if x["theme_code"] == code), None)
            prev_item = prev_issue_map.get(code)

            curr_share = curr_item["prevalence_pct"] if curr_item else 0.0
            prev_share = prev_item["prevalence_pct"] if prev_item else 0.0
            share_delta = round(curr_share - prev_share, 2)

            curr_crit = curr_item["critical_count"] if curr_item else 0
            prev_crit = prev_item["critical_count"] if prev_item else 0

            # Classification of trajectory
            if prev_item is None and curr_item is not None:
                trajectory_status = "Emerging / New"
            elif curr_item is None and prev_item is not None:
                trajectory_status = "Resolved / Not Observed"
            elif share_delta <= -3.0:
                trajectory_status = "Improving"
            elif share_delta >= 3.0:
                trajectory_status = "Worsening"
            else:
                trajectory_status = "Persistent / Stable"

            theme_name = (curr_item or prev_item).get("theme_name", code)

            trajectories.append({
                "theme_code": code,
                "theme_name": theme_name,
                "status": trajectory_status,
                "current_critical_count": curr_crit,
                "previous_critical_count": prev_crit,
                "current_share_pct": curr_share,
                "previous_share_pct": prev_share,
                "share_delta_pct": share_delta,
                "current_rank": curr_item.get("priority_rank") if curr_item else None,
                "previous_rank": prev_item.get("priority_rank") if prev_item else None
            })

        # Sort trajectories by current critical count descending
        trajectories.sort(key=lambda x: x["current_critical_count"], reverse=True)

        return {
            "has_previous_period": True,
            "current_period": current_run.get("reporting_period"),
            "previous_period": previous_run.get("reporting_period"),
            "volume": {
                "current": curr_vol,
                "previous": prev_vol,
                "delta": vol_delta,
                "pct_change": vol_pct
            },
            "rating": {
                "current": curr_rating,
                "previous": prev_rating,
                "delta": rating_delta
            },
            "critical_pct": {
                "current": curr_critical_pct,
                "previous": prev_critical_pct,
                "delta": critical_pct_delta
            },
            "theme_trajectories": trajectories,
            "version_patterns": cls.extract_version_patterns(current_reviews),
            "summary": (
                f"Review volume changed by {vol_delta:+d} ({vol_pct:+.1f}%), "
                f"sample rating shifted by {rating_delta:+.2f} stars, "
                f"and critical complaint proportion changed by {critical_pct_delta:+.1f}% pts."
            )
        }

    @staticmethod
    def extract_version_patterns(reviews: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyzes complaint rate and average rating broken down by app version."""
        if not reviews:
            return []
        df = pd.DataFrame(reviews)
        if "app_version" not in df.columns:
            return []

        version_stats = []
        for ver, g in df.groupby("app_version"):
            count = len(g)
            if count < 5:
                continue # Skip negligible sample versions
            avg_score = round(float(g["score"].mean()), 2)
            crit_count = int((g["score"] <= 2).sum())
            crit_rate = round(crit_count / count * 100, 1)

            top_theme = g[g["score"] <= 2]["primary_theme"].mode()
            top_complaint = top_theme.iloc[0] if not top_theme.empty else "N/A"

            version_stats.append({
                "version": ver,
                "total_reviews": count,
                "avg_rating": avg_score,
                "critical_count": crit_count,
                "critical_rate_pct": crit_rate,
                "top_complaint_theme": top_complaint
            })

        version_stats.sort(key=lambda x: x["total_reviews"], reverse=True)
        return version_stats
