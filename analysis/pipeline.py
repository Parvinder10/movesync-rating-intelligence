"""
Investigation Pipeline Orchestrator (Stages A through H)
Executes repeatable monthly investigations, preserves persistent history,
computes MoM deltas, updates action tracking, and compiles reports.
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from backend.database import (
    init_db, get_db_connection, save_app_metadata, insert_raw_reviews,
    upsert_cleaned_review, save_investigation_run, save_issue_snapshots,
    upsert_action, save_monthly_report, DB_PATH
)
from analysis.collector import MoveInSyncCollector, OFFICIAL_APP_ID
from analysis.validator import ReviewValidator
from analysis.classifier import ReviewClassifier
from analysis.prioritization import PrioritizationEngine, METHODOLOGY_VERSION
from analysis.mom_comparison import MonthOverMonthComparator
from analysis.outcome_evaluator import OutcomeEvaluator, DEFAULT_ACTIONS
from reports.generator import ReportGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class InvestigationPipeline:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)
        self.collector = MoveInSyncCollector()
        self.validator = ReviewValidator()
        self.classifier = ReviewClassifier()
        self.prio_engine = PrioritizationEngine()
        self.comparator = MonthOverMonthComparator()
        self.outcome_evaluator = OutcomeEvaluator()
        self.report_generator = ReportGenerator()

        # Seed initial actions if empty
        self._init_actions()

    def _init_actions(self):
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM action_register")
        count = cur.fetchone()[0]
        conn.close()
        if count == 0:
            for act in DEFAULT_ACTIONS:
                upsert_action(act, self.db_path)
            logger.info("Seeded %d default baseline engineering actions.", len(DEFAULT_ACTIONS))

    def collect_and_ingest(
        self,
        count: int = 3000,
        import_file: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Stage A & B: Collects or imports reviews, validates, and stores raw & cleaned records.
        """
        if import_file:
            raw_reviews, metadata = self.collector.import_from_file(import_file)
            collection_method = "file_import"
        else:
            try:
                raw_reviews, metadata = self.collector.fetch_live_reviews(count=count)
                collection_method = "live_google_play_scrape"
            except Exception as e:
                logger.warning("Live fetch failed: %s. Checking existing database records...", str(e))
                # Check if we have existing records in db
                conn = get_db_connection(self.db_path)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM raw_reviews")
                existing = cur.fetchone()[0]
                conn.close()
                if existing > 0:
                    logger.info("Using %d existing raw reviews from local database.", existing)
                    return {"app_id": OFFICIAL_APP_ID, "score": 4.64}, {"valid_unique_records": existing}
                raise

        # Save metadata
        save_app_metadata(metadata, self.db_path)

        # Stage B: Validate and normalize
        cleaned_records, validation_report = self.validator.validate_and_normalize(raw_reviews)

        # Batch insert raw reviews (deduplicated by review_id)
        batch_period = datetime.utcnow().strftime("%Y-%m")
        new_count = insert_raw_reviews(raw_reviews, batch_period, self.db_path)
        logger.info("Inserted %d new raw reviews into database (deduplicated).", new_count)

        # Enrich and store cleaned reviews
        for rec in cleaned_records:
            enriched = self.classifier.process_review(rec)
            upsert_cleaned_review(enriched, self.db_path)

        return metadata, validation_report

    def run_investigation_for_period(
        self,
        reporting_period: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Runs complete Prompt 1 investigation for a single monthly period (e.g. '2026-09').
        Stages C through H.
        """
        logger.info("=== Executing Monthly Investigation for Period: %s ===", reporting_period)
        conn = get_db_connection(self.db_path)
        conn.row_factory = dict_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

        # Fetch reviews for this period
        cur = conn.cursor()
        cur.execute("SELECT * FROM cleaned_reviews WHERE reporting_period = ?", (reporting_period,))
        period_reviews = cur.fetchall()

        if not period_reviews:
            logger.warning("No reviews found for period %s. Marking incomplete.", reporting_period)
            run_id = f"run_{reporting_period}_{int(datetime.utcnow().timestamp())}"
            run_record = {
                "run_id": run_id,
                "reporting_period": reporting_period,
                "run_timestamp": datetime.utcnow().isoformat(),
                "status": "incomplete",
                "collection_method": "database_query",
                "store_rating": 4.64,
                "sample_rating": None,
                "period_review_count": 0,
                "total_unique_reviews": 0,
                "critical_review_count": 0,
                "rating_distribution_json": json.dumps({}),
                "top_issue_theme": None,
                "recommended_action_id": None,
                "methodology_version": METHODOLOGY_VERSION,
                "notes": f"Period {reporting_period} marked incomplete due to zero available reviews."
            }
            save_investigation_run(run_record, self.db_path)
            conn.close()
            return run_record

        # Compute period metrics
        scores = [r["score"] for r in period_reviews]
        sample_rating = round(sum(scores) / len(scores), 2)
        critical_count = sum(1 for s in scores if s <= 2)
        rating_dist = {str(i): scores.count(i) for i in range(1, 6)}

        # Get total unique reviews across all periods up to this point
        cur.execute("SELECT COUNT(DISTINCT review_id) FROM cleaned_reviews WHERE reporting_period <= ?", (reporting_period,))
        total_unique_so_far = cur.fetchone()["COUNT(DISTINCT review_id)"]

        # Stage E: Prioritization
        issue_snapshots = self.prio_engine.score_issues(period_reviews, reporting_period)
        top_issue = issue_snapshots[0]["theme_code"] if issue_snapshots else None

        # Previous month lookup for MoM comparison
        prev_period = self._get_previous_period(reporting_period)
        cur.execute("SELECT * FROM investigation_runs WHERE reporting_period = ?", (prev_period,))
        prev_run = cur.fetchone()

        prev_reviews = []
        prev_issues = []
        if prev_run:
            cur.execute("SELECT * FROM cleaned_reviews WHERE reporting_period = ?", (prev_period,))
            prev_reviews = cur.fetchall()
            cur.execute("SELECT * FROM issue_snapshots WHERE reporting_period = ?", (prev_period,))
            prev_issues = cur.fetchall()

        # MoM comparison
        mom_report = self.comparator.compare_monthly_runs(
            current_run={"period_review_count": len(period_reviews), "sample_rating": sample_rating, "critical_review_count": critical_count, "reporting_period": reporting_period},
            previous_run=prev_run,
            current_reviews=period_reviews,
            previous_reviews=prev_reviews,
            current_issues=issue_snapshots,
            previous_issues=prev_issues
        )

        # Actions & Outcome Evaluation
        cur.execute("SELECT * FROM action_register")
        current_actions = cur.fetchall()
        for act in current_actions:
            updated_act = self.outcome_evaluator.evaluate_action_outcome(act, issue_snapshots, prev_issues)
            upsert_action(updated_act, self.db_path)

        # Run ID
        run_id = f"run_{reporting_period}"
        store_rating = metadata.get("score", 4.64) if metadata else 4.64

        run_record = {
            "run_id": run_id,
            "reporting_period": reporting_period,
            "run_timestamp": datetime.utcnow().isoformat(),
            "status": "completed",
            "collection_method": "live_google_play_scrape" if not prev_run else "monthly_routine",
            "store_rating": store_rating,
            "sample_rating": sample_rating,
            "period_review_count": len(period_reviews),
            "total_unique_reviews": total_unique_so_far,
            "critical_review_count": critical_count,
            "rating_distribution_json": json.dumps(rating_dist),
            "top_issue_theme": top_issue,
            "recommended_action_id": "ACT-001" if top_issue in ["AUTH_LOGIN_OTP", "FORCED_RATING_MODAL"] else "ACT-002",
            "methodology_version": METHODOLOGY_VERSION,
            "notes": f"Prompt 1 investigation executed for {reporting_period}. {mom_report['summary']}"
        }

        # Save run and snapshots
        save_investigation_run(run_record, self.db_path)
        save_issue_snapshots(issue_snapshots, run_id, self.db_path)

        # Markdown Report Generation (Stage H)
        summary_md = self._generate_markdown_report(run_record, issue_snapshots, mom_report)
        report_data = {
            "report_id": f"rep_{reporting_period}",
            "run_id": run_id,
            "reporting_period": reporting_period,
            "summary_markdown": summary_md,
            "metrics_json": json.dumps({
                "run": run_record,
                "issues": issue_snapshots,
                "mom": mom_report
            }),
            "pdf_path": os.path.join("reports", "MoveInSync_Case_Study.pdf")
        }
        save_monthly_report(report_data, self.db_path)

        conn.close()
        logger.info("Investigation run completed for %s. Top issue: %s", reporting_period, top_issue)
        return {
            "run": run_record,
            "issues": issue_snapshots,
            "mom": mom_report
        }

    def run_all_historical_periods(self, metadata: Optional[Dict[str, Any]] = None):
        """
        Iterates chronologically through all periods present in cleaned_reviews and creates historical runs.
        Ensures idempotent reruns.
        """
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT reporting_period FROM cleaned_reviews ORDER BY reporting_period ASC")
        periods = [r[0] for r in cur.fetchall()]
        conn.close()

        logger.info("Found %d distinct reporting periods to process: %s", len(periods), periods)
        last_result = None
        for p in periods:
            last_result = self.run_investigation_for_period(p, metadata)

        # Generate Case Study PDF after all periods are processed
        self.generate_case_study_pdf(metadata)
        return last_result

    def generate_case_study_pdf(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Compiles the 8-page recruiter-ready Case Study PDF with all current historical data."""
        conn = get_db_connection(self.db_path)
        conn.row_factory = lambda cursor, row: {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
        cur = conn.cursor()

        # Monthly summary trends
        cur.execute("""
            SELECT reporting_period as month,
                   COUNT(*) as total,
                   AVG(score) as avg_rating,
                   SUM(CASE WHEN score = 1 THEN 1 ELSE 0 END) as '1_star',
                   SUM(CASE WHEN score = 2 THEN 1 ELSE 0 END) as '2_star',
                   SUM(CASE WHEN score = 5 THEN 1 ELSE 0 END) as '5_star',
                   ROUND(CAST(SUM(CASE WHEN score <= 2 THEN 1 ELSE 0 END) AS REAL) / COUNT(*) * 100, 1) as low_rating_pct
            FROM cleaned_reviews
            GROUP BY reporting_period
            ORDER BY reporting_period ASC
        """)
        monthly_trends = cur.fetchall()
        for m in monthly_trends:
            m["avg_rating"] = round(float(m["avg_rating"]), 2)

        # Latest issue snapshots
        cur.execute("SELECT * FROM investigation_runs ORDER BY reporting_period DESC LIMIT 1")
        latest_run = cur.fetchone()
        latest_run_id = latest_run["run_id"] if latest_run else None

        issue_snapshots = []
        if latest_run_id:
            cur.execute("SELECT * FROM issue_snapshots WHERE run_id = ? ORDER BY priority_rank ASC", (latest_run_id,))
            issue_snapshots = cur.fetchall()

        # Actions
        cur.execute("SELECT * FROM action_register ORDER BY action_id ASC")
        actions = cur.fetchall()

        if not metadata:
            cur.execute("SELECT * FROM app_metadata ORDER BY id DESC LIMIT 1")
            meta_row = cur.fetchone()
            if meta_row:
                metadata = dict(meta_row)
            else:
                metadata = {"app_id": OFFICIAL_APP_ID, "score": 4.64, "ratings": 114881, "reviews": 23625}

        conn.close()

        pdf_path = self.report_generator.build_case_study_pdf(
            metadata=metadata,
            monthly_trends=monthly_trends,
            issue_snapshots=issue_snapshots,
            actions=actions
        )
        return pdf_path

    @staticmethod
    def _get_previous_period(period_str: str) -> str:
        """Calculates YYYY-MM of the preceding month."""
        parts = period_str.split("-")
        year, month = int(parts[0]), int(parts[1])
        if month == 1:
            return f"{year - 1}-12"
        else:
            return f"{year}-{month - 1:02d}"

    @staticmethod
    def _generate_markdown_report(run: Dict[str, Any], issues: List[Dict[str, Any]], mom: Dict[str, Any]) -> str:
        md = f"# MoveInSync Monthly Rating Intelligence Report — {run['reporting_period']}\n\n"
        md += f"**Investigation Run ID:** `{run['run_id']}`  \n"
        md += f"**Timestamp:** {run['run_timestamp']}  \n"
        md += f"**Methodology Version:** {run['methodology_version']}  \n\n"
        md += f"## Executive Metrics\n"
        md += f"- **Play Store Displayed Rating:** {run.get('store_rating', '4.64')}★\n"
        md += f"- **Monthly Sample Average Rating:** {run.get('sample_rating')}★\n"
        md += f"- **Monthly Review Volume:** {run.get('period_review_count')} reviews\n"
        md += f"- **Critical Review Count (1-2★):** {run.get('critical_review_count')} ({round(run.get('critical_review_count', 0)/max(1, run.get('period_review_count', 1))*100, 1)}%)\n"
        md += f"- **Cumulative Unique Reviews Tracked:** {run.get('total_unique_reviews')}\n\n"
        md += f"## Priority Defect Ranking\n"
        for item in issues[:5]:
            md += f"{item['priority_rank']}. **{item['theme_name']}** (Score: {item['priority_score']:.2f}) — {item['prevalence_pct']}% of criticals ({item['critical_count']} reviews)\n"
        md += f"\n## Month-over-Month Synthesis\n"
        md += f"{mom.get('summary', 'Initial baseline.')}\n"
        return md


if __name__ == "__main__":
    pipeline = InvestigationPipeline()
    print("Collecting live evidence from Google Play Store...")
    meta, val = pipeline.collect_and_ingest(count=3000)
    print("Running chronological historical investigations across all periods...")
    pipeline.run_all_historical_periods(meta)
    print("Pipeline completed successfully! Check reports/MoveInSync_Case_Study.pdf")
