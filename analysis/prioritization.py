"""
Stage E: Prioritization Engine Module
Applies a documented, reproducible multi-factor scoring model to rank issues:
Priority Score = (Prevalence * 0.30) + (Severity * 0.30) + (Impact * 0.20) + (Confidence * 0.10) - (Effort * 0.10)
"""

import math
from typing import Dict, List, Any, Optional
import pandas as pd
from analysis.classifier import THEME_TAXONOMY

METHODOLOGY_VERSION = "1.0.0"

# Enterprise impact weights for corporate B2B commute SLAs
ENTERPRISE_IMPACT_WEIGHTS = {
    "CAB_ALLOCATION_DELAYS": 9.5,
    "DRIVER_BEHAVIOR_NOSHOW": 9.0,
    "LIVE_TRACKING_GPS": 8.5,
    "AUTH_LOGIN_OTP": 8.0,
    "APP_PERFORMANCE_CRASH": 7.5,
    "BOOKING_SCHEDULING": 6.5,
    "FORCED_RATING_MODAL": 6.0,
    "NOTIFICATIONS_ALERTS": 5.0,
    "GENERAL_DISSATISFACTION": 4.0,
    "POSITIVE_EXPERIENCE": 1.0,
    "NEUTRAL_GENERAL": 2.0
}


class PrioritizationEngine:
    @staticmethod
    def calculate_confidence(review_count: int) -> float:
        """Derives statistical confidence from sample volume."""
        if review_count >= 50:
            return 9.5
        elif review_count >= 25:
            return 8.5
        elif review_count >= 15:
            return 7.5
        elif review_count >= 8:
            return 6.0
        elif review_count >= 3:
            return 4.5
        else:
            return 3.0

    @classmethod
    def score_issues(
        cls,
        period_reviews: List[Dict[str, Any]],
        reporting_period: str
    ) -> List[Dict[str, Any]]:
        """
        Calculates issue priority scores and rankings for a given reporting period.
        """
        if not period_reviews:
            return []

        df = pd.DataFrame(period_reviews)
        total_period_reviews = len(df)
        critical_df = df[df["score"] <= 2]
        total_critical = len(critical_df)

        issue_rows = []

        # Group by primary theme
        theme_groups = df.groupby("primary_theme")

        for theme_code, group in theme_groups:
            if theme_code in ["POSITIVE_EXPERIENCE", "NEUTRAL_GENERAL"]:
                continue # Exclude non-issues from defect prioritization register

            meta = THEME_TAXONOMY.get(theme_code, {})
            theme_name = meta.get("name", theme_code.replace("_", " ").title())
            review_count = len(group)
            crit_count = len(group[group["score"] <= 2])
            avg_rating = round(float(group["score"].mean()), 2)

            # 1. Prevalence (Proportion of critical complaints in the period)
            prevalence_pct = round((crit_count / total_critical * 100), 2) if total_critical > 0 else 0.0
            # Normalized prevalence score [1.0 .. 10.0]
            prevalence_score = min(10.0, max(1.0, round((prevalence_pct / 3.0), 2)))

            # 2. Severity (Impact on commute viability)
            severity_score = float(meta.get("severity_weight", 6.0))

            # 3. Business Impact (Corporate SLA breaches & churn risk)
            impact_score = ENTERPRISE_IMPACT_WEIGHTS.get(theme_code, 6.0)

            # 4. Confidence (Evidence volume)
            confidence_score = cls.calculate_confidence(crit_count)

            # 5. Effort (Complexity to implement fix)
            effort_score = float(meta.get("effort_weight", 5.0))

            # Multi-factor formula:
            # Score = (P * 0.30) + (S * 0.30) + (I * 0.20) + (C * 0.10) - (E * 0.10)
            raw_priority = (
                (prevalence_score * 0.30) +
                (severity_score * 0.30) +
                (impact_score * 0.20) +
                (confidence_score * 0.10) -
                (effort_score * 0.10)
            )
            priority_score = round(max(0.0, raw_priority), 2)

            # Collect representative review IDs
            sample_ids = group.sort_values(by="score", ascending=True)["review_id"].head(5).tolist()

            issue_rows.append({
                "snapshot_id": f"snap_{reporting_period}_{theme_code}",
                "reporting_period": reporting_period,
                "theme_code": theme_code,
                "theme_name": theme_name,
                "review_count": review_count,
                "critical_count": crit_count,
                "prevalence_pct": prevalence_pct,
                "avg_rating": avg_rating,
                "prevalence_score": prevalence_score,
                "severity_score": severity_score,
                "impact_score": impact_score,
                "confidence_score": confidence_score,
                "effort_score": effort_score,
                "priority_score": priority_score,
                "sample_review_ids": sample_ids,
                "root_cause_hypothesis": meta.get("root_cause_hypothesis", ""),
                "unresolved_questions": meta.get("unresolved_questions", "")
            })

        # Sort descending by priority_score
        issue_rows.sort(key=lambda x: x["priority_score"], reverse=True)

        # Assign ranks
        for idx, item in enumerate(issue_rows):
            item["priority_rank"] = idx + 1

        return issue_rows

    @classmethod
    def compare_rankings(
        cls,
        current_issues: List[Dict[str, Any]],
        previous_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calculates rank deltas between current and previous month.
        """
        prev_map = {item["theme_code"]: item for item in previous_issues}
        compared = []

        for curr in current_issues:
            code = curr["theme_code"]
            prev = prev_map.get(code)
            item_copy = dict(curr)
            if prev:
                prev_rank = prev["priority_rank"]
                rank_delta = prev_rank - curr["priority_rank"] # Positive means moved up in urgency
                score_delta = round(curr["priority_score"] - prev["priority_score"], 2)
                item_copy["prev_rank"] = prev_rank
                item_copy["rank_delta"] = rank_delta
                item_copy["prev_priority_score"] = prev["priority_score"]
                item_copy["score_delta"] = score_delta
                item_copy["is_new"] = False
            else:
                item_copy["prev_rank"] = None
                item_copy["rank_delta"] = 0
                item_copy["prev_priority_score"] = None
                item_copy["score_delta"] = 0.0
                item_copy["is_new"] = True
            compared.append(item_copy)

        return compared
