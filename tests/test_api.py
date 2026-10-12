"""
Integration tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)


def test_api_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_app_info():
    response = client.get("/api/app-info")
    assert response.status_code == 200
    data = response.json()
    assert data["app_id"] == "com.moveinsync.ets"
    assert data["verified"] is True
    assert data["store_rating"] > 4.0


def test_api_investigation_latest():
    response = client.get("/api/investigation/latest")
    assert response.status_code == 200
    data = response.json()
    assert "run" in data
    assert "issues" in data
    assert len(data["issues"]) > 0


def test_api_reviews_filter():
    response = client.get("/api/reviews?score=1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert "reviews" in data
    assert len(data["reviews"]) <= 5
    for r in data["reviews"]:
        assert r["score"] == 1


def test_api_priorities():
    response = client.get("/api/priorities")
    assert response.status_code == 200
    data = response.json()
    assert "issues" in data
    assert len(data["issues"]) > 0


def test_api_comparison():
    response = client.get("/api/comparison")
    assert response.status_code == 200
    data = response.json()
    assert "volume" in data
    assert "rating" in data


def test_api_actions():
    response = client.get("/api/actions")
    assert response.status_code == 200
    data = response.json()
    assert "actions" in data
    assert len(data["actions"]) >= 3


def test_api_export_csv():
    response = client.get("/api/export/reviews.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "review_id" in response.text


def test_api_recommendations_playbook():
    response = client.get("/api/recommendations/playbook")
    assert response.status_code == 200
    data = response.json()
    assert "playbook" in data
    assert len(data["playbook"]) >= 3


def test_api_recommendation_detail():
    response = client.get("/api/recommendations/ACT-001")
    assert response.status_code == 200
    data = response.json()
    assert data["action_id"] == "ACT-001"
    assert "what_to_improve" in data
    assert "how_to_improve" in data


def test_api_download_pdf():
    response = client.get("/api/reports/latest/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 100000

