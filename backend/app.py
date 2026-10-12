"""
Backend API Service for MoveSync Rating Intelligence System
FastAPI application serving investigation data, evidence explorer,
month-over-month comparisons, action tracker, improvement playbooks, and report downloads.
"""

import os
import io
import csv
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, APIRouter, HTTPException, Query, Path, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from backend.database import get_db_connection, DB_PATH
from analysis.pipeline import InvestigationPipeline
from analysis.prioritization import PrioritizationEngine
from analysis.mom_comparison import MonthOverMonthComparator
from analysis.improvement_playbook import get_all_playbook_actions, get_playbook_action

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backend.app")

app = FastAPI(
    title="MoveSync Rating Intelligence API",
    description="Recurring monthly investigation, defect prioritization, and outcome tracking system.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = InvestigationPipeline(DB_PATH)
router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "database": os.path.exists(DB_PATH)}


@router.get("/app-info")
def get_app_info():
    """Returns official verified MoveInSync application identity and listing metadata."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM app_metadata ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "app_id": "com.moveinsync.ets",
            "title": "MoveInSync",
            "developer": "MoveInSync: Enabling Hybrid Workplaces",
            "store_rating": 4.64,
            "total_ratings": 114881,
            "total_reviews": 23625,
            "installs": "1,000,000+",
            "genre": "Maps & Navigation",
            "current_version": "12.19.0",
            "verified": True,
            "source": "Google Play Store (India)"
        }

    return {
        "app_id": row["app_id"],
        "title": row["title"],
        "developer": row["developer"],
        "store_rating": row["store_rating"],
        "total_ratings": row["total_ratings"],
        "total_reviews": row["total_reviews"],
        "installs": row["installs"],
        "genre": row["genre"],
        "current_version": row["current_version"],
        "collected_at": row["collected_at"],
        "verified": True,
        "source": "Google Play Store (India)"
    }


@router.get("/investigation/latest")
def get_latest_investigation():
    """Returns overview of the latest completed monthly investigation."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM investigation_runs ORDER BY reporting_period DESC LIMIT 1")
    run = cur.fetchone()

    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail="No completed investigation runs found.")

    run_dict = dict(run)
    run_dict["rating_distribution"] = json.loads(run["rating_distribution_json"])

    # Fetch top issues
    cur.execute("SELECT * FROM issue_snapshots WHERE run_id = ? ORDER BY priority_rank ASC", (run["run_id"],))
    issues = [dict(r) for r in cur.fetchall()]
    for i in issues:
        i["sample_review_ids"] = json.loads(i["sample_review_ids_json"])

    # Fetch recommended action
    cur.execute("SELECT * FROM action_register WHERE action_id = ?", (run["recommended_action_id"],))
    action = cur.fetchone()

    conn.close()
    return {
        "run": run_dict,
        "issues": issues,
        "recommended_action": dict(action) if action else None
    }


@router.get("/investigation/runs")
def list_investigation_runs():
    """Returns chronological list of all recorded monthly investigation runs."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM investigation_runs ORDER BY reporting_period DESC")
    runs = [dict(r) for r in cur.fetchall()]
    for r in runs:
        r["rating_distribution"] = json.loads(r["rating_distribution_json"]) if r.get("rating_distribution_json") else {}
    conn.close()
    return {"runs": runs}


@router.get("/investigation/{period}")
def get_investigation_by_period(period: str = Path(..., description="Reporting period format YYYY-MM")):
    """Returns investigation details for a specific month."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM investigation_runs WHERE reporting_period = ?", (period,))
    run = cur.fetchone()

    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No investigation run found for period: {period}")

    run_dict = dict(run)
    run_dict["rating_distribution"] = json.loads(run["rating_distribution_json"]) if run.get("rating_distribution_json") else {}

    cur.execute("SELECT * FROM issue_snapshots WHERE run_id = ? ORDER BY priority_rank ASC", (run["run_id"],))
    issues = [dict(r) for r in cur.fetchall()]
    for i in issues:
        i["sample_review_ids"] = json.loads(i["sample_review_ids_json"])

    conn.close()
    return {"run": run_dict, "issues": issues}


@router.post("/investigation/run")
def trigger_investigation_run(
    period: str = Body(..., embed=True, description="Reporting period e.g. '2026-10'"),
    collect_live: bool = Body(False, embed=True, description="Fetch fresh reviews from Google Play Store")
):
    """
    Executes a monthly investigation workflow on demand.
    Supports live scraping or running against verified stored reviews.
    """
    logger.info("Triggered investigation for period: %s (collect_live=%s)", period, collect_live)
    try:
        metadata = None
        if collect_live:
            metadata, _ = pipeline.collect_and_ingest(count=1000)

        result = pipeline.run_investigation_for_period(period, metadata)
        pipeline.generate_case_study_pdf(metadata)

        return {
            "status": "success",
            "message": f"Monthly investigation for {period} completed successfully.",
            "data": result
        }
    except Exception as e:
        logger.error("Investigation run failed: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Investigation execution failed: {str(e)}")


@router.get("/reviews")
def get_reviews(
    query: Optional[str] = Query(None, description="Search keyword in review text"),
    score: Optional[int] = Query(None, description="Filter by star score (1-5)"),
    theme: Optional[str] = Query(None, description="Filter by primary theme code"),
    period: Optional[str] = Query(None, description="Filter by reporting period YYYY-MM"),
    version: Optional[str] = Query(None, description="Filter by app version string"),
    is_critical: Optional[bool] = Query(None, description="Filter critical reviews (1-2 stars)"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0)
):
    """Evidence Explorer: Search and filter actual reviews with traceability."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()

    conditions = []
    params = []

    if query:
        conditions.append("c.cleaned_content LIKE ?")
        params.append(f"%{query}%")
    if score is not None:
        conditions.append("c.score = ?")
        params.append(score)
    if theme:
        conditions.append("c.primary_theme = ?")
        params.append(theme)
    if period:
        conditions.append("c.reporting_period = ?")
        params.append(period)
    if version:
        conditions.append("c.app_version = ?")
        params.append(version)
    if is_critical is not None:
        conditions.append("c.is_critical = ?")
        params.append(1 if is_critical else 0)

    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

    count_sql = f"SELECT COUNT(*) FROM cleaned_reviews c {where_clause}"
    cur.execute(count_sql, params)
    total_count = cur.fetchone()[0]

    data_sql = f"""
        SELECT c.*, r.user_name, r.thumbs_up_count, r.reply_content, r.at
        FROM cleaned_reviews c
        JOIN raw_reviews r ON c.review_id = r.review_id
        {where_clause}
        ORDER BY r.at DESC
        LIMIT ? OFFSET ?
    """
    cur.execute(data_sql, params + [limit, offset])
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return {
        "total": total_count,
        "limit": limit,
        "offset": offset,
        "reviews": rows
    }


@router.get("/priorities")
def get_priorities(period: Optional[str] = Query(None, description="Reporting period; defaults to latest")):
    """Returns prioritized issues and multi-factor scoring for the specified or latest period."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()

    if not period:
        cur.execute("SELECT reporting_period FROM investigation_runs ORDER BY reporting_period DESC LIMIT 1")
        row = cur.fetchone()
        period = row["reporting_period"] if row else "2026-10"

    cur.execute("SELECT * FROM investigation_runs WHERE reporting_period = ?", (period,))
    run = cur.fetchone()
    if not run:
        conn.close()
        raise HTTPException(status_code=404, detail=f"No data for period {period}")

    cur.execute("SELECT * FROM issue_snapshots WHERE run_id = ? ORDER BY priority_rank ASC", (run["run_id"],))
    issues = [dict(r) for r in cur.fetchall()]
    for i in issues:
        i["sample_review_ids"] = json.loads(i["sample_review_ids_json"])

    prev_period = pipeline._get_previous_period(period)
    cur.execute("SELECT * FROM investigation_runs WHERE reporting_period = ?", (prev_period,))
    prev_run = cur.fetchone()
    prev_issues = []
    if prev_run:
        cur.execute("SELECT * FROM issue_snapshots WHERE run_id = ? ORDER BY priority_rank ASC", (prev_run["run_id"],))
        prev_issues = [dict(r) for r in cur.fetchall()]

    compared_issues = PrioritizationEngine.compare_rankings(issues, prev_issues)
    conn.close()

    return {
        "reporting_period": period,
        "methodology_version": run["methodology_version"],
        "issues": compared_issues
    }


@router.get("/comparison")
def get_month_over_month_comparison(
    current_period: Optional[str] = Query(None),
    previous_period: Optional[str] = Query(None)
):
    """Compares metrics, theme trajectories, and version distributions between two periods."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()

    if not current_period:
        cur.execute("SELECT reporting_period FROM investigation_runs ORDER BY reporting_period DESC LIMIT 1")
        row = cur.fetchone()
        current_period = row["reporting_period"] if row else "2026-10"

    if not previous_period:
        previous_period = pipeline._get_previous_period(current_period)

    cur.execute("SELECT * FROM investigation_runs WHERE reporting_period = ?", (current_period,))
    curr_run = cur.fetchone()
    cur.execute("SELECT * FROM investigation_runs WHERE reporting_period = ?", (previous_period,))
    prev_run = cur.fetchone()

    cur.execute("SELECT * FROM cleaned_reviews WHERE reporting_period = ?", (current_period,))
    curr_reviews = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT * FROM cleaned_reviews WHERE reporting_period = ?", (previous_period,))
    prev_reviews = [dict(r) for r in cur.fetchall()] if prev_run else []

    cur.execute("SELECT * FROM issue_snapshots WHERE reporting_period = ? ORDER BY priority_rank ASC", (current_period,))
    curr_issues = [dict(r) for r in cur.fetchall()]
    cur.execute("SELECT * FROM issue_snapshots WHERE reporting_period = ? ORDER BY priority_rank ASC", (previous_period,))
    prev_issues = [dict(r) for r in cur.fetchall()] if prev_run else []

    conn.close()

    comparison = MonthOverMonthComparator.compare_monthly_runs(
        current_run=dict(curr_run) if curr_run else {"period_review_count": len(curr_reviews), "reporting_period": current_period},
        previous_run=dict(prev_run) if prev_run else None,
        current_reviews=curr_reviews,
        previous_reviews=prev_reviews,
        current_issues=curr_issues,
        previous_issues=prev_issues
    )

    return comparison


@router.get("/actions")
def get_actions():
    """Returns persistent action register with evidence links and outcome statuses."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM action_register ORDER BY action_id ASC")
    actions = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"actions": actions}


@router.patch("/actions/{action_id}")
def update_action(
    action_id: str = Path(...),
    status: Optional[str] = Body(None),
    verified_evidence: Optional[str] = Body(None),
    latest_metric_value: Optional[float] = Body(None),
    outcome_label: Optional[str] = Body(None),
    next_decision: Optional[str] = Body(None)
):
    """Updates action status, implementation evidence, and outcome labels."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM action_register WHERE action_id = ?", (action_id,))
    act = cur.fetchone()
    if not act:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Action {action_id} not found.")

    act_dict = dict(act)
    if status is not None:
        act_dict["status"] = status
    if verified_evidence is not None:
        act_dict["verified_evidence"] = verified_evidence
    if latest_metric_value is not None:
        act_dict["latest_metric_value"] = latest_metric_value
    if outcome_label is not None:
        act_dict["outcome_label"] = outcome_label
    if next_decision is not None:
        act_dict["next_decision"] = next_decision

    cur.execute("""
        UPDATE action_register
        SET status = ?, verified_evidence = ?, latest_metric_value = ?, outcome_label = ?, next_decision = ?
        WHERE action_id = ?
    """, (
        act_dict["status"],
        act_dict["verified_evidence"],
        act_dict["latest_metric_value"],
        act_dict["outcome_label"],
        act_dict["next_decision"],
        action_id
    ))
    conn.commit()
    conn.close()
    return {"status": "success", "action": act_dict}


@router.get("/recommendations/playbook")
def get_recommendations_playbook():
    """
    Returns the comprehensive engineering improvement playbook for all recommended actions,
    detailing WHAT should be improved and HOW to improve it.
    """
    return {"playbook": get_all_playbook_actions()}


@router.get("/recommendations/{action_id}")
def get_recommendation_detail(action_id: str = Path(..., description="Action ID e.g. ACT-001")):
    """
    Returns detailed diagnosis (WHAT to improve) and engineering roadmap (HOW to improve)
    for a specific recommended action.
    """
    plan = get_playbook_action(action_id)
    if not plan:
        raise HTTPException(status_code=404, detail=f"Improvement playbook not found for {action_id}")
    return plan


@router.get("/reports")
def list_reports():
    """Lists generated monthly reports."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT report_id, reporting_period, created_at, pdf_path FROM monthly_reports ORDER BY reporting_period DESC")
    reports = [dict(r) for r in cur.fetchall()]
    conn.close()
    return {"reports": reports}


@router.get("/reports/{period}/pdf")
def download_pdf(period: str):
    """Serves the generated case study PDF report."""
    pdf_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "MoveInSync_Case_Study.pdf")
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Case study PDF has not been generated yet.")
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename="MoveInSync_Case_Study.pdf"
    )


@router.get("/export/reviews.csv")
def export_reviews_csv(period: Optional[str] = Query(None)):
    """Exports cleaned review evidence dataset to CSV."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    if period:
        cur.execute("SELECT c.*, r.user_name, r.at FROM cleaned_reviews c JOIN raw_reviews r ON c.review_id = r.review_id WHERE c.reporting_period = ? ORDER BY r.at DESC", (period,))
    else:
        cur.execute("SELECT c.*, r.user_name, r.at FROM cleaned_reviews c JOIN raw_reviews r ON c.review_id = r.review_id ORDER BY r.at DESC")
    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow(list(r))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=movesync_reviews_{period or 'all'}.csv"}
    )


@router.get("/export/issues.csv")
def export_issues_csv(period: Optional[str] = Query(None)):
    """Exports prioritized issue snapshots to CSV."""
    conn = get_db_connection(DB_PATH)
    cur = conn.cursor()
    if period:
        cur.execute("SELECT * FROM issue_snapshots WHERE reporting_period = ? ORDER BY priority_rank ASC", (period,))
    else:
        cur.execute("SELECT * FROM issue_snapshots ORDER BY reporting_period DESC, priority_rank ASC")
    rows = cur.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    if rows:
        writer.writerow(rows[0].keys())
        for r in rows:
            writer.writerow(list(r))

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=movesync_issues_{period or 'all'}.csv"}
    )


# Attach router both with prefix /api and at root for full serverless flexibility
app.include_router(router, prefix="/api")
app.include_router(router)

# Serve frontend static assets and root page
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
PUBLIC_DIR = os.path.join(ROOT_DIR, "public")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_frontend_root():
    for candidate in [
        os.path.join(PUBLIC_DIR, "index.html"),
        os.path.join(FRONTEND_DIR, "index.html")
    ]:
        if os.path.exists(candidate):
            return FileResponse(candidate)
    return {"status": "ok", "app": "MoveSync Rating Intelligence"}
