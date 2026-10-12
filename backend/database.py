"""
Database schema and persistence layer for MoveSync Rating Intelligence System.
Uses SQLite for zero-dependency, local-first, reproducible historical storage.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "movesync_intelligence.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DB_PATH):
    """Initializes tables for reviews, investigation runs, issue snapshots, actions, and reports."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    -- 1. App Metadata Snapshot
    CREATE TABLE IF NOT EXISTS app_metadata (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        app_id TEXT NOT NULL,
        title TEXT NOT NULL,
        developer TEXT NOT NULL,
        store_rating REAL NOT NULL,
        total_ratings INTEGER NOT NULL,
        total_reviews INTEGER NOT NULL,
        installs TEXT NOT NULL,
        genre TEXT NOT NULL,
        current_version TEXT,
        collected_at TEXT NOT NULL
    );

    -- 2. Raw Reviews (Immutable capture, deduplicated by review_id)
    CREATE TABLE IF NOT EXISTS raw_reviews (
        review_id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        user_name TEXT,
        user_image TEXT,
        content TEXT,
        score INTEGER NOT NULL,
        thumbs_up_count INTEGER DEFAULT 0,
        review_created_version TEXT,
        app_version TEXT,
        at TEXT NOT NULL,
        reply_content TEXT,
        replied_at TEXT,
        batch_period TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    );

    -- 3. Cleaned & Enriched Reviews
    CREATE TABLE IF NOT EXISTS cleaned_reviews (
        review_id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        cleaned_content TEXT,
        score INTEGER NOT NULL,
        sentiment TEXT NOT NULL,
        sentiment_score REAL NOT NULL,
        primary_theme TEXT NOT NULL,
        secondary_theme TEXT,
        review_date TEXT NOT NULL,
        reporting_period TEXT NOT NULL,
        app_version TEXT,
        has_developer_reply INTEGER DEFAULT 0,
        is_critical INTEGER DEFAULT 0,
        FOREIGN KEY (review_id) REFERENCES raw_reviews(review_id) ON DELETE CASCADE
    );

    -- 4. Monthly Investigation Runs
    CREATE TABLE IF NOT EXISTS investigation_runs (
        run_id TEXT PRIMARY KEY,
        reporting_period TEXT UNIQUE NOT NULL,
        run_timestamp TEXT NOT NULL,
        status TEXT NOT NULL,
        collection_method TEXT NOT NULL,
        store_rating REAL,
        sample_rating REAL,
        period_review_count INTEGER NOT NULL,
        total_unique_reviews INTEGER NOT NULL,
        critical_review_count INTEGER NOT NULL,
        rating_distribution_json TEXT NOT NULL,
        top_issue_theme TEXT,
        recommended_action_id TEXT,
        methodology_version TEXT NOT NULL,
        notes TEXT
    );

    -- 5. Issue Snapshots Per Investigation Run
    CREATE TABLE IF NOT EXISTS issue_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        reporting_period TEXT NOT NULL,
        theme_code TEXT NOT NULL,
        theme_name TEXT NOT NULL,
        review_count INTEGER NOT NULL,
        critical_count INTEGER NOT NULL,
        prevalence_pct REAL NOT NULL,
        avg_rating REAL NOT NULL,
        severity_score REAL NOT NULL,
        prevalence_score REAL NOT NULL,
        impact_score REAL NOT NULL,
        confidence_score REAL NOT NULL,
        effort_score REAL NOT NULL,
        priority_score REAL NOT NULL,
        priority_rank INTEGER NOT NULL,
        sample_review_ids_json TEXT NOT NULL,
        root_cause_hypothesis TEXT,
        unresolved_questions TEXT,
        FOREIGN KEY (run_id) REFERENCES investigation_runs(run_id) ON DELETE CASCADE
    );

    -- 6. Action Register (Interventions & Outcome Tracking)
    CREATE TABLE IF NOT EXISTS action_register (
        action_id TEXT PRIMARY KEY,
        issue_theme TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        first_step TEXT NOT NULL,
        owner TEXT NOT NULL,
        priority_level TEXT NOT NULL,
        status TEXT NOT NULL, -- proposed, investigating, in_progress, implemented, evaluated, blocked
        proposed_start_date TEXT,
        target_review_date TEXT,
        verified_evidence TEXT,
        baseline_metric_name TEXT NOT NULL,
        baseline_metric_value REAL NOT NULL,
        target_metric_value REAL NOT NULL,
        latest_metric_value REAL,
        outcome_label TEXT NOT NULL, -- pending, inconclusive, observed_association, positive_shift, adverse_shift
        limitations TEXT,
        next_decision TEXT
    );

    -- 7. Monthly Reports Reference
    CREATE TABLE IF NOT EXISTS monthly_reports (
        report_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        reporting_period TEXT UNIQUE NOT NULL,
        summary_markdown TEXT NOT NULL,
        metrics_json TEXT NOT NULL,
        pdf_path TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (run_id) REFERENCES investigation_runs(run_id) ON DELETE CASCADE
    );

    -- Indices for fast filtering
    CREATE INDEX IF NOT EXISTS idx_raw_at ON raw_reviews(at);
    CREATE INDEX IF NOT EXISTS idx_clean_period ON cleaned_reviews(reporting_period);
    CREATE INDEX IF NOT EXISTS idx_clean_theme ON cleaned_reviews(primary_theme);
    CREATE INDEX IF NOT EXISTS idx_clean_score ON cleaned_reviews(score);
    CREATE INDEX IF NOT EXISTS idx_issue_run ON issue_snapshots(run_id);
    """);

    conn.commit()
    conn.close()


def save_app_metadata(meta: Dict[str, Any], db_path: str = DB_PATH) -> int:
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO app_metadata (app_id, title, developer, store_rating, total_ratings, total_reviews, installs, genre, current_version, collected_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        meta.get('app_id', 'com.moveinsync.ets'),
        meta.get('title', 'MoveInSync'),
        meta.get('developer', 'MoveInSync: Enabling Hybrid Workplaces'),
        float(meta.get('score', 0.0)),
        int(meta.get('ratings', 0)),
        int(meta.get('reviews', 0)),
        str(meta.get('installs', '1,000,000+')),
        str(meta.get('genre', 'Maps & Navigation')),
        str(meta.get('version', '')),
        datetime.utcnow().isoformat()
    ))
    row_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return row_id


def insert_raw_reviews(reviews: List[Dict[str, Any]], batch_period: str, db_path: str = DB_PATH) -> int:
    """Inserts raw reviews with review_id deduplication. Returns count of new reviews inserted."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    new_count = 0
    now = datetime.utcnow().isoformat()

    for r in reviews:
        review_id = str(r['reviewId'])
        score = int(r.get('score', 1))
        content = str(r.get('content') or '')
        user_name = str(r.get('userName') or 'Anonymous')
        user_image = str(r.get('userImage') or '')
        thumbs = int(r.get('thumbsUpCount', 0))
        ver = str(r.get('reviewCreatedVersion') or r.get('appVersion') or '')
        app_ver = str(r.get('appVersion') or ver)
        
        at_val = r.get('at')
        if isinstance(at_val, datetime):
            at_str = at_val.isoformat()
        else:
            at_str = str(at_val)

        reply_content = r.get('replyContent')
        replied_at = r.get('repliedAt')
        if isinstance(replied_at, datetime):
            replied_at = replied_at.isoformat()
        elif replied_at is not None:
            replied_at = str(replied_at)

        try:
            cursor.execute("""
                INSERT INTO raw_reviews (
                    review_id, app_id, user_name, user_image, content, score,
                    thumbs_up_count, review_created_version, app_version, at,
                    reply_content, replied_at, batch_period, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                review_id, 'com.moveinsync.ets', user_name, user_image, content, score,
                thumbs, ver, app_ver, at_str, reply_content, replied_at, batch_period, now
            ))
            new_count += 1
        except sqlite3.IntegrityError:
            # Already exists - preserve original record without duplication
            continue

    conn.commit()
    conn.close()
    return new_count


def upsert_cleaned_review(clean_data: Dict[str, Any], db_path: str = DB_PATH):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO cleaned_reviews (
            review_id, app_id, cleaned_content, score, sentiment, sentiment_score,
            primary_theme, secondary_theme, review_date, reporting_period,
            app_version, has_developer_reply, is_critical
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        clean_data['review_id'],
        clean_data.get('app_id', 'com.moveinsync.ets'),
        clean_data['cleaned_content'],
        clean_data['score'],
        clean_data['sentiment'],
        clean_data['sentiment_score'],
        clean_data['primary_theme'],
        clean_data.get('secondary_theme'),
        clean_data['review_date'],
        clean_data['reporting_period'],
        clean_data.get('app_version'),
        clean_data.get('has_developer_reply', 0),
        clean_data.get('is_critical', 0)
    ))
    conn.commit()
    conn.close()


def save_investigation_run(run_data: Dict[str, Any], db_path: str = DB_PATH):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO investigation_runs (
            run_id, reporting_period, run_timestamp, status, collection_method,
            store_rating, sample_rating, period_review_count, total_unique_reviews,
            critical_review_count, rating_distribution_json, top_issue_theme,
            recommended_action_id, methodology_version, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        run_data['run_id'],
        run_data['reporting_period'],
        run_data['run_timestamp'],
        run_data['status'],
        run_data['collection_method'],
        run_data.get('store_rating'),
        run_data.get('sample_rating'),
        run_data['period_review_count'],
        run_data['total_unique_reviews'],
        run_data['critical_review_count'],
        run_data['rating_distribution_json'],
        run_data.get('top_issue_theme'),
        run_data.get('recommended_action_id'),
        run_data.get('methodology_version', '1.0.0'),
        run_data.get('notes', '')
    ))
    conn.commit()
    conn.close()


def save_issue_snapshots(snapshots: List[Dict[str, Any]], run_id: str, db_path: str = DB_PATH):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM issue_snapshots WHERE run_id = ?", (run_id,))
    for s in snapshots:
        cursor.execute("""
            INSERT INTO issue_snapshots (
                snapshot_id, run_id, reporting_period, theme_code, theme_name,
                review_count, critical_count, prevalence_pct, avg_rating,
                severity_score, prevalence_score, impact_score, confidence_score,
                effort_score, priority_score, priority_rank, sample_review_ids_json,
                root_cause_hypothesis, unresolved_questions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            s['snapshot_id'],
            run_id,
            s['reporting_period'],
            s['theme_code'],
            s['theme_name'],
            s['review_count'],
            s['critical_count'],
            s['prevalence_pct'],
            s['avg_rating'],
            s['severity_score'],
            s['prevalence_score'],
            s['impact_score'],
            s['confidence_score'],
            s['effort_score'],
            s['priority_score'],
            s['priority_rank'],
            json.dumps(s.get('sample_review_ids', [])),
            s.get('root_cause_hypothesis', ''),
            s.get('unresolved_questions', '')
        ))
    conn.commit()
    conn.close()


def upsert_action(action: Dict[str, Any], db_path: str = DB_PATH):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO action_register (
            action_id, issue_theme, title, description, first_step, owner,
            priority_level, status, proposed_start_date, target_review_date,
            verified_evidence, baseline_metric_name, baseline_metric_value,
            target_metric_value, latest_metric_value, outcome_label, limitations, next_decision
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        action['action_id'],
        action['issue_theme'],
        action['title'],
        action['description'],
        action['first_step'],
        action['owner'],
        action['priority_level'],
        action['status'],
        action.get('proposed_start_date'),
        action.get('target_review_date'),
        action.get('verified_evidence'),
        action['baseline_metric_name'],
        float(action['baseline_metric_value']),
        float(action['target_metric_value']),
        float(action['latest_metric_value']) if action.get('latest_metric_value') is not None else None,
        action.get('outcome_label', 'pending'),
        action.get('limitations', ''),
        action.get('next_decision', '')
    ))
    conn.commit()
    conn.close()


def save_monthly_report(report_data: Dict[str, Any], db_path: str = DB_PATH):
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO monthly_reports (
            report_id, run_id, reporting_period, summary_markdown, metrics_json, pdf_path, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        report_data['report_id'],
        report_data['run_id'],
        report_data['reporting_period'],
        report_data['summary_markdown'],
        report_data['metrics_json'],
        report_data.get('pdf_path'),
        report_data.get('created_at', datetime.utcnow().isoformat())
    ))
    conn.commit()
    conn.close()
