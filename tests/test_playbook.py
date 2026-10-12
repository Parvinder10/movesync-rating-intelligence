"""
Unit tests for the Engineering Improvement Playbook module.
Verifies that all recommendations contain required 'what_to_improve' and 'how_to_improve' structures.
"""

import pytest
from analysis.improvement_playbook import get_all_playbook_actions, get_playbook_action


def test_get_all_playbook_actions():
    actions = get_all_playbook_actions()
    assert len(actions) >= 3
    action_ids = [a["action_id"] for a in actions]
    assert "ACT-001" in action_ids
    assert "ACT-002" in action_ids
    assert "ACT-003" in action_ids


def test_playbook_act_001_structure():
    plan = get_playbook_action("ACT-001")
    assert plan is not None
    assert plan["priority_level"].startswith("P0")
    assert "what_to_improve" in plan
    assert "how_to_improve" in plan

    # Verify 'what_to_improve' components
    w = plan["what_to_improve"]
    assert "core_problem" in w
    assert "affected_journey_stage" in w
    assert "baseline_metric" in w
    assert "target_metric" in w
    assert len(w["evidence_citations"]) >= 2

    # Verify 'how_to_improve' components
    h = plan["how_to_improve"]
    assert "architectural_solution" in h
    assert len(h["implementation_steps"]) >= 3
    assert len(h["technical_stack_impact"]) >= 2
    assert "rollout_and_experimentation" in h
    assert len(h["guardrails_and_risks"]) >= 1
    assert "expected_outcome" in h


def test_playbook_act_002_and_003():
    for act_id in ["ACT-002", "ACT-003"]:
        plan = get_playbook_action(act_id)
        assert plan is not None
        assert "what_to_improve" in plan
        assert "how_to_improve" in plan
        assert len(plan["how_to_improve"]["implementation_steps"]) >= 3
