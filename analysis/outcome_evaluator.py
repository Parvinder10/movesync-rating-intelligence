"""
Stage F & G: Engineering Action & Outcome Tracking Engine
Maintains the verified Action Register, evaluates measurable outcomes against
baseline metrics, and strictly enforces non-causal attribution guidelines.
"""

from typing import Dict, List, Any, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)

# Canonical initial baseline actions derived from empirical evidence
DEFAULT_ACTIONS = [
    {
        "action_id": "ACT-001",
        "issue_theme": "FORCED_RATING_MODAL",
        "title": "Decouple In-App Ride Rating from Screen Access & Add Dismiss Option",
        "description": (
            "Remove the blocking, unskippable ride-rating dialog that traps employees after rides, "
            "and eliminate the intrusive seatbelt safety popup overlaying the 'View OTP' button."
        ),
        "first_step": "Deploy client-side feature flag to convert post-trip rating modal into a non-blocking toast/card with an explicit 'Skip' button.",
        "owner": "Mobile Platform & Passenger UX",
        "priority_level": "P0 - Critical Quick Win",
        "status": "in_progress",
        "proposed_start_date": "2026-09-01",
        "target_review_date": "2026-10-31",
        "verified_evidence": "User reviews in v12.19 explicitly report giving 1-star reviews on Play Store because the in-app modal had no skip button.",
        "baseline_metric_name": "Forced Rating & OTP Friction Share (%)",
        "baseline_metric_value": 14.5,
        "target_metric_value": 3.0,
        "latest_metric_value": 11.2,
        "outcome_label": "observed_association",
        "limitations": "Reviewers on older app versions (prior to v12.19 hotfix) still experience modal trapping; Play Store review delay lags client release.",
        "next_decision": "Verify rollout percentage across corporate client tenants; mandate app update for tenants reporting high login/OTP friction."
    },
    {
        "action_id": "ACT-002",
        "issue_theme": "LIVE_TRACKING_GPS",
        "title": "Foreground Location Service & Adaptive GPS Polling Synchronization",
        "description": (
            "Fix driver-to-passenger location sync lag by enforcing foreground location pings "
            "during active trips and upgrading passenger client ETA calculation with real-time waypoint detours."
        ),
        "first_step": "Audit MoveInSync Partner Lite background execution limits on OEM battery-saver Android devices; enforce foreground service pings.",
        "owner": "Driver Mobility & Routing Engineering",
        "priority_level": "P1 - High",
        "status": "investigating",
        "proposed_start_date": "2026-09-15",
        "target_review_date": "2026-11-15",
        "verified_evidence": "Multiple user reviews cite vehicle stationary markers and ETA discrepancy (3x Google Maps time) under 1 hour to trip.",
        "baseline_metric_name": "Live Tracking Complaint Share (%)",
        "baseline_metric_value": 18.2,
        "target_metric_value": 8.0,
        "latest_metric_value": 16.8,
        "outcome_label": "inconclusive",
        "limitations": "Driver device GPS hardware diversity and poor mobile network reception in basement pickup zones introduce external confounders.",
        "next_decision": "Deploy lightweight network-resilient MQTT location stream test on top 3 enterprise corporate hubs."
    },
    {
        "action_id": "ACT-003",
        "issue_theme": "DRIVER_BEHAVIOR_NOSHOW",
        "title": "Geofence Enforcement & Passenger Call Verification Before Ride Cancellation",
        "description": (
            "Prevent driver false no-shows by requiring GPS proximity within 50 meters of the pickup point "
            "for at least 3 minutes and an automated server call ping before allowing 'Passenger Absent' status."
        ),
        "first_step": "Implement backend validation rule rejecting driver 'No-Show' requests if driver coordinate distance to stop > 50m.",
        "owner": "Transport Operations & Vendor Governance",
        "priority_level": "P1 - High",
        "status": "proposed",
        "proposed_start_date": "2026-10-01",
        "target_review_date": "2026-12-01",
        "verified_evidence": "Employees report drivers dropping rides or marking no-show without calling or reaching the corporate pickup gate.",
        "baseline_metric_name": "Driver Conduct & No-Show Complaint Share (%)",
        "baseline_metric_value": 15.5,
        "target_metric_value": 6.0,
        "latest_metric_value": 15.5,
        "outcome_label": "pending",
        "limitations": "Requires coordination with third-party cab vendors and driver training compliance.",
        "next_decision": "Present rule change to vendor council and run pilot in Bangalore tech park zone."
    }
]


class OutcomeEvaluator:
    @staticmethod
    def evaluate_action_outcome(
        action: Dict[str, Any],
        current_issues: List[Dict[str, Any]],
        previous_issues: Optional[List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Updates action latest_metric_value and outcome_label based on observed evidence.
        Applies strict non-causal guardrails.
        """
        updated = dict(action)
        theme = action.get("issue_theme")
        status = action.get("status")

        # Find current theme prevalence
        curr_item = next((x for x in current_issues if x["theme_code"] == theme), None)
        if curr_item:
            current_prevalence = curr_item["prevalence_pct"]
            updated["latest_metric_value"] = current_prevalence

            baseline = action.get("baseline_metric_value", current_prevalence)
            target = action.get("target_metric_value", current_prevalence)

            if status in ["proposed", "investigating"]:
                updated["outcome_label"] = "pending"
            elif status in ["in_progress", "implemented"]:
                delta = current_prevalence - baseline
                if delta <= -3.0:
                    # Significant drop in complaint share
                    updated["outcome_label"] = "observed_association"
                elif delta >= 3.0:
                    # Increase in complaint share
                    updated["outcome_label"] = "adverse_shift"
                else:
                    updated["outcome_label"] = "inconclusive"
            elif status == "evaluated":
                updated["outcome_label"] = "observed_association" if current_prevalence <= target else "inconclusive"
        else:
            if status in ["proposed", "investigating"]:
                updated["outcome_label"] = "pending"
            else:
                updated["outcome_label"] = "inconclusive"

        return updated
