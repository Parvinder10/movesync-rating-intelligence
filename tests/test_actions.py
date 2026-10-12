"""
Unit tests for OutcomeEvaluator and non-causal guardrails.
"""

import pytest
from analysis.outcome_evaluator import OutcomeEvaluator


def test_action_evaluation_in_progress():
    action = {
        "action_id": "ACT-001",
        "issue_theme": "FORCED_RATING_MODAL",
        "status": "in_progress",
        "baseline_metric_value": 15.0,
        "target_metric_value": 5.0
    }
    # Current prevalence dropped by 5%
    current_issues = [{"theme_code": "FORCED_RATING_MODAL", "prevalence_pct": 10.0}]
    evaluated = OutcomeEvaluator.evaluate_action_outcome(action, current_issues, None)

    assert evaluated["latest_metric_value"] == 10.0
    # Drop >= 3.0% gives 'observed_association' (strictly non-causal label)
    assert evaluated["outcome_label"] == "observed_association"


def test_action_evaluation_inconclusive():
    action = {
        "action_id": "ACT-002",
        "issue_theme": "LIVE_TRACKING_GPS",
        "status": "in_progress",
        "baseline_metric_value": 18.0,
        "target_metric_value": 8.0
    }
    # Current prevalence shifted by only 0.5%
    current_issues = [{"theme_code": "LIVE_TRACKING_GPS", "prevalence_pct": 17.5}]
    evaluated = OutcomeEvaluator.evaluate_action_outcome(action, current_issues, None)

    assert evaluated["latest_metric_value"] == 17.5
    assert evaluated["outcome_label"] == "inconclusive"
