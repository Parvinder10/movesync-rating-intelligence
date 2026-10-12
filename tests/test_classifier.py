"""
Unit tests for ReviewClassifier and sentiment engine.
"""

import pytest
from analysis.classifier import ReviewClassifier


def test_classify_live_tracking_issue():
    text = "ETA calculator very bad. Location map not moving and wrong location shown for van."
    primary, secondary, matched = ReviewClassifier.classify_review(text, score=1)
    assert primary == "LIVE_TRACKING_GPS"
    assert any(k in ["eta", "location", "map"] for k in matched)


def test_classify_forced_rating_modal():
    text = "Forcing me to give rating after every ride with no skip option. Annoying popup modal."
    primary, secondary, matched = ReviewClassifier.classify_review(text, score=1)
    assert primary == "FORCED_RATING_MODAL"


def test_classify_auth_otp():
    text = "When I click view otp it pops up seat belt safely. Cannot login easily."
    primary, secondary, matched = ReviewClassifier.classify_review(text, score=1)
    assert primary == "AUTH_LOGIN_OTP"


def test_sentiment_scoring():
    # Strong negative
    sent_neg, score_neg = ReviewClassifier.compute_sentiment("Worst pathetic app, completely useless disaster!", score=1)
    assert sent_neg == "negative"
    assert score_neg < -0.3

    # Strong positive
    sent_pos, score_pos = ReviewClassifier.compute_sentiment("Super comfortable ride, excellent punctual driver, great experience!", score=5)
    assert sent_pos == "positive"
    assert score_pos > 0.3
