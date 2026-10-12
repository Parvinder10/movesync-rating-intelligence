# Data Dictionary & Schema Reference

Database: `data/movesync_intelligence.db` (SQLite)

---

## 1. `app_metadata`
Stores verified Google Play Store listing snapshots for MoveInSync.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | INTEGER (PK) | Auto-incrementing identifier. |
| `app_id` | TEXT | Official package identifier (`com.moveinsync.ets`). |
| `title` | TEXT | Application display title. |
| `developer` | TEXT | Developer organization name. |
| `store_rating` | REAL | Play Store displayed rating (e.g. 4.64★). |
| `total_ratings` | INTEGER | Lifetime ratings count (114,881). |
| `total_reviews` | INTEGER | Lifetime text review count (23,625). |
| `installs` | TEXT | Play Store install bracket (e.g. '1,000,000+'). |
| `genre` | TEXT | Play Store category ('Maps & Navigation'). |
| `current_version`| TEXT | Current production version string (e.g. '12.19.0'). |
| `collected_at` | TEXT (ISO) | Ingestion timestamp. |

---

## 2. `raw_reviews`
Immutable store of raw incoming reviews from Google Play or verified fallback import files.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `review_id` | TEXT (PK) | Google Play unique review UUID or deterministic SHA-256 fallback. |
| `app_id` | TEXT | Package identifier. |
| `user_name` | TEXT | User display name or pseudonym. |
| `user_image` | TEXT | User avatar URI. |
| `content` | TEXT | Verbatim user review text. |
| `score` | INTEGER | Star rating integer [1..5]. |
| `thumbs_up_count`| INTEGER | Public helpful vote count. |
| `review_created_version` | TEXT | App version at time review was posted. |
| `app_version` | TEXT | Fallback version string. |
| `at` | TEXT (ISO) | Submission timestamp. |
| `reply_content` | TEXT | Public MoveInSync developer response text if provided. |
| `replied_at` | TEXT (ISO) | Timestamp of developer response. |
| `batch_period` | TEXT | Ingestion period format YYYY-MM. |
| `fetched_at` | TEXT (ISO) | Timestamp record was written to DB. |

---

## 3. `cleaned_reviews`
Sanitized, deduplicated, enriched review records with computed sentiment and primary/secondary defect themes.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `review_id` | TEXT (PK, FK) | References `raw_reviews(review_id)`. |
| `app_id` | TEXT | Package identifier. |
| `cleaned_content`| TEXT | Cleaned review text with normalized whitespace. |
| `score` | INTEGER | Verified star score [1..5]. |
| `sentiment` | TEXT | Sentiment label: `positive`, `neutral`, `negative`. |
| `sentiment_score`| REAL | Continuous sentiment score [-1.0 .. 1.0]. |
| `primary_theme` | TEXT | Top matched defect theme code. |
| `secondary_theme`| TEXT | Secondary matched defect theme code if present. |
| `review_date` | TEXT | Submission date formatted `YYYY-MM-DD`. |
| `reporting_period`| TEXT | Monthly period formatted `YYYY-MM`. |
| `app_version` | TEXT | Cleaned version string. |
| `has_developer_reply` | INTEGER | 1 if developer replied, 0 otherwise. |
| `is_critical` | INTEGER | 1 if score $\le 2$, 0 otherwise. |

---

## 4. `investigation_runs`
Preserves historical metadata for every monthly investigation execution.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `run_id` | TEXT (PK) | Unique run identifier (e.g. `run_2026-10`). |
| `reporting_period`| TEXT (UNIQUE) | Monthly period (`YYYY-MM`). |
| `run_timestamp` | TEXT (ISO) | Timestamp investigation was executed. |
| `status` | TEXT | Run outcome: `completed`, `incomplete`, `failed`. |
| `collection_method`| TEXT | Method: `live_google_play_scrape`, `file_import`. |
| `store_rating` | REAL | Play Store displayed rating at time of run. |
| `sample_rating` | REAL | Average star rating of sample reviews in period. |
| `period_review_count` | INTEGER | Total reviews logged in this monthly period. |
| `total_unique_reviews` | INTEGER | Cumulative deduplicated reviews across history. |
| `critical_review_count` | INTEGER | Number of 1★ and 2★ reviews in period. |
| `rating_distribution_json` | TEXT | JSON map of counts for star ratings 1 through 5. |
| `top_issue_theme` | TEXT | Primary defect theme code ranked #1. |
| `recommended_action_id` | TEXT | Primary engineering intervention ID (e.g. `ACT-001`). |
| `methodology_version` | TEXT | Version of analytical scoring model (`1.0.0`). |
| `notes` | TEXT | Operational notes and synthesis summary. |

---

## 5. `issue_snapshots`
Defect-level metrics and multi-factor priority scores captured for each monthly run.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `snapshot_id` | TEXT (PK) | E.g. `snap_2026-10_LIVE_TRACKING_GPS`. |
| `run_id` | TEXT (FK) | References `investigation_runs(run_id)`. |
| `reporting_period`| TEXT | Monthly period (`YYYY-MM`). |
| `theme_code` | TEXT | Issue theme identifier. |
| `theme_name` | TEXT | Human-readable issue title. |
| `review_count` | INTEGER | Total reviews mentioning theme in period. |
| `critical_count` | INTEGER | 1★ and 2★ reviews mentioning theme. |
| `prevalence_pct`| REAL | Proportion of all critical reviews in period (%). |
| `avg_rating` | REAL | Average star rating of reviews in theme. |
| `severity_score`| REAL | Commute disruption severity weight [1..10]. |
| `prevalence_score`| REAL | Normalized prevalence score [1..10]. |
| `impact_score` | REAL | Enterprise B2B SLA breach risk [1..10]. |
| `confidence_score`| REAL | Evidence sample volume confidence [1..10]. |
| `effort_score` | REAL | Engineering & operations overhead discount [1..10]. |
| `priority_score`| REAL | Computed multi-factor priority score. |
| `priority_rank` | INTEGER | Sequential ranking (1 = most urgent). |
| `sample_review_ids_json` | TEXT | JSON list of representative review UUIDs. |
| `root_cause_hypothesis` | TEXT | Technical root cause diagnosis hypothesis. |
| `unresolved_questions` | TEXT | Questions requiring internal telemetry to answer. |

---

## 6. `action_register`
Persistent action tracker connecting recommendations to quantifiable outcomes.

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `action_id` | TEXT (PK) | Action identifier (e.g. `ACT-001`). |
| `issue_theme` | TEXT | Associated defect theme code. |
| `title` | TEXT | Engineering intervention title. |
| `description` | TEXT | Detailed specification of fix. |
| `first_step` | TEXT | Concrete first implementation task. |
| `owner` | TEXT | Responsible engineering or operations squad. |
| `priority_level`| TEXT | E.g. `P0 - Critical Quick Win`, `P1 - High`. |
| `status` | TEXT | `proposed`, `investigating`, `in_progress`, `implemented`, `evaluated`, `blocked`. |
| `proposed_start_date` | TEXT | ISO date format. |
| `target_review_date` | TEXT | Scheduled outcome review date. |
| `verified_evidence` | TEXT | References to specific user complaints justifying fix. |
| `baseline_metric_name` | TEXT | Quantifiable target metric name. |
| `baseline_metric_value`| REAL | Measured metric value prior to release. |
| `target_metric_value` | REAL | 60-day target metric value. |
| `latest_metric_value` | REAL | Observed metric value in current period. |
| `outcome_label` | TEXT | Strictly non-causal: `pending`, `observed_association`, `inconclusive`, `adverse_shift`. |
| `limitations` | TEXT | Known confounders (e.g. version lag, tenant rules). |
| `next_decision` | TEXT | Concrete next decision for the squad. |
