# System Architecture & Technical Specifications

The **MoveSync Rating Intelligence System** is an enterprise-grade, recurring monthly investigation, defect prioritization, and outcome tracking engine for **MoveInSync** (`com.moveinsync.ets`).

## 1. High-Level Architecture

The system is built on a modular, local-first Python + FastAPI architecture designed for reproducibility, historical snapshot integrity, and zero third-party lock-in.

```
+---------------------------------------------------------------------------------+
|                        PUBLIC SOURCES & EVIDENCE INGESTION                     |
|                                                                                 |
|  Google Play Store Listing           Fallback File Importer (JSON/CSV)          |
|  (com.moveinsync.ets)                (Auditable Public Evidence Snapshots)      |
+---------------------------------------------------------------------------------+
                                       │
                                       ▼
+---------------------------------------------------------------------------------+
|                      STAGE A & B: COLLECTION & VALIDATION                       |
|                                                                                 |
|  MoveInSyncCollector                 ReviewValidator                            |
|  • Live metadata & reviews batching  • Schema checking (1..5★, ISO dates)       |
|  • Raw snapshot archival (data/raw/) • Review UUID deduplication                |
+---------------------------------------------------------------------------------+
                                       │
                                       ▼
+---------------------------------------------------------------------------------+
|                   PERSISTENT STORAGE LAYER (SQLite Database)                   |
|                                                                                 |
|  • app_metadata                      • raw_reviews (immutable)                  |
|  • cleaned_reviews (enriched)        • investigation_runs                       |
|  • issue_snapshots                   • action_register                          |
|  • monthly_reports                   (Local DB: data/movesync_intelligence.db)  |
+---------------------------------------------------------------------------------+
                                       │
                                       ▼
+---------------------------------------------------------------------------------+
|                STAGE C, D, E & F: ANALYSIS & PRIORITIZATION ENGINE              |
|                                                                                 |
|  ReviewClassifier                    PrioritizationEngine                       |
|  • Empirical taxonomy keyword match  • Multi-factor formula scoring             |
|  • Hybrid sentiment [-1.0..1.0]      • Rank deltas (Current vs Previous)        |
|                                                                                 |
|  MonthOverMonthComparator            OutcomeEvaluator                           |
|  • Volume, rating, critical deltas   • Baseline metric tracking                 |
|  • Trajectory classification         • Non-causal guardrails                    |
+---------------------------------------------------------------------------------+
                                       │
                     ┌─────────────────┴─────────────────┐
                     ▼                                   ▼
+------------------------------------------+  +-----------------------------------+
|       FASTAPI REST API & DASHBOARD       |  |      REPORTS & PDF ARTIFACTS      |
|                                          |  |                                   |
|  • Evidence Explorer (/api/reviews)      |  |  • 8-Page Case Study PDF          |
|  • Priority Register (/api/priorities)   |  |    (reports/MoveInSync_Case_Study)|
|  • MoM Comparison (/api/comparison)      |  |  • Monthly Markdown Summaries     |
|  • Action Tracker (/api/actions)         |  |  • CSV Evidence Exports           |
|  • Monthly Run Trigger (/api/run)        |  |  • High-res Matplotlib Charts     |
+------------------------------------------+  +-----------------------------------+
```

## 2. Core Modules Breakdown

### `analysis/collector.py`
- Connects to Google Play Store using `google-play-scraper`.
- Gathers official app metadata: ratings, reviews, current version, developer info.
- Gathers review batches sorted by newest.
- Provides file import fallback for JSON/CSV formats when offline.
- Writes raw immutable JSON snapshots to `data/raw/`.

### `analysis/validator.py`
- Enforces strict data types: ratings clamped [1..5], timestamps parsed to ISO.
- Deduplicates incoming reviews by `reviewId`. For records missing a reviewId, generates a deterministic SHA-256 fallback hash (`gen_<hash>`).
- Normalizes and sanitizes whitespace and empty strings.

### `analysis/classifier.py`
- Employs an empirical keyword-and-rule pattern classifier matching user complaints to 9 verified categories.
- Computes hybrid continuous sentiment [-1.0 to +1.0] blending star ratings and lexical indicators.
- Emits root-cause hypotheses and unresolved diagnostic questions.

### `analysis/prioritization.py`
- Implements the documented multi-factor scoring formula:
  $$\text{Priority Score} = (P \times 0.30) + (S \times 0.30) + (I \times 0.20) + (C \times 0.10) - (E \times 0.10)$$
- Ranks issues descending by priority score.
- Computes MoM rank shifts ($\Delta \text{Rank}$).

### `analysis/mom_comparison.py`
- Analyzes volume delta ($\Delta N$), rating shifts ($\Delta \text{Rating}$), and critical review proportion shifts.
- Classifies defect trajectories into:
  - *Emerging / New*: Observed in current period, absent in previous.
  - *Improving*: Complaint share dropped by $\ge 3.0\%$.
  - *Worsening*: Complaint share increased by $\ge 3.0\%$.
  - *Persistent / Stable*: Shift within $\pm 3.0\%$.
- Extracts version patterns analyzing complaint rates by app release.

### `analysis/outcome_evaluator.py`
- Connects verified engineering actions in the Action Register to observable issue metrics.
- Enforces scientific non-causal guardrails: outcomes labeled as `observed_association`, `inconclusive`, or `pending`.

### `reports/generator.py`
- Builds the 8-page recruiter-ready Case Study PDF using ReportLab and Matplotlib.
- Employs `NumberedCanvas` for dynamic "Page X of 8" pagination.
- Renders high-resolution vector and raster charts.

### `backend/app.py`
- Serves full RESTful API for dashboard integration and export endpoints.
- Serves the Single Page Application dashboard with responsive Tailwind CSS.
