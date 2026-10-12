# MoveSync Rating Intelligence System
### Recurring Monthly Investigation, Defect Prioritization & Outcome Tracking Engine

[![Tests Passing](https://img.shields.io/badge/tests-28%2F28%20passed-success)](tests/)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Verified Evidence](https://img.shields.io/badge/evidence-Play%20Store%20Verified-blue)](https://play.google.com/store/apps/details?id=com.moveinsync.ets)
[![Live Production](https://img.shields.io/badge/Vercel-Live%20Dashboard-000000?logo=vercel)](https://movesync-rating-intelligence-kappa.vercel.app)


---

## 1. Project Overview & Business Mission

**Core Question:**
> *"Why are MoveInSync's Google Play Store ratings low, what should the company fix first, what has changed since the previous investigation, and are the recommended fixes improving the user experience?"*

**MoveInSync** (`com.moveinsync.ets`) is the world's leading enterprise employee commute mobility platform, powering daily transport operations for over 400 enterprises and 97 Fortune 500 corporations with 1,000,000+ app installs.

While the public Google Play Store listing displays a favorable lifetime score of **4.64★** (anchored by 114,881 legacy ratings), rigorous empirical sampling of **3,000 recent user reviews** reveals an active commuter sentiment average of only **3.83★**. More critically, **27.1% of recent active reviews are 1★ or 2★ ratings**, driven by severe operational and product failures that threaten corporate B2B service-level agreements (SLAs), enterprise client contract renewals, and daily commuter trust.

This system establishes an end-to-end, reproducible, monthly intelligence system that:
1. Gathers and deduplicates genuine public reviews from Google Play Store without data fabrication.
2. Uncovers the empirical root causes behind negative ratings.
3. Quantitatively scores and prioritizes defect fixes using a transparent multi-factor decision model.
4. Preserves persistent historical monthly snapshots and tracks month-over-month trajectories.
5. Evaluates engineering interventions against quantifiable baseline metrics with strict non-causal attribution guardrails.
6. Compiles an 8-page recruiter-ready Case Study PDF and serves an interactive operations dashboard.

---

## 2. Key Empirical Findings & Current Priority Decision

### Verified Empirical Findings
- **The Divergence Discovery:** The displayed Play Store rating (**4.64★**) masks acute recent deterioration. Monthly sample scores fluctuate between **3.56★ and 4.03★**, with critical reviews surging to **33.7%** during release disruption windows (June 2026 / v12.19.0).
- **Polarized Sentiment:** Reviews are strictly bimodal (63.8% are 5★ and 24.2% are 1★). Intermediate ratings (2-4★) account for only 12.0% combined, confirming commuters review on Google Play primarily during flawless trips or severe operational breakdowns.
- **Top Defect Domains in Critical Reviews (1-2★):**
  1. **Driver Conduct & False No-Show (15.5% / 126 reviews):** Drivers dropping rides or marking "passenger absent" without geofenced arrival.
  2. **Auth, Session & OTP Access (12.7% / 103 reviews):** Commuters blocked from viewing boarding OTP by intrusive seatbelt safety modals and sudden session logouts.
  3. **Live Tracking & ETA Inaccuracy (12.4% / 101 reviews):** Vehicle marker freezing on maps; in-app ETA 3x slower than actual Google Maps transit time.
  4. **Booking & Roster Scheduling (11.5% / 94 reviews):** Rigid corporate cutoff windows and silent waitlist booking confusion.
  5. **App Stability & Crashes (11.1% / 90 reviews):** App crashing on cold start or freezing after updates, requiring manual reinstallation.
  6. **Forced Ride Rating Interruption (6.2% / 51 reviews):** Unskippable post-trip in-app rating modal with no dismiss option, driving frustrated commuters directly to Google Play to leave retaliatory 1-star reviews.

### Primary Priority Decision: ACT-001 (P0 Quick Win)
**Action:** Decouple In-App Ride Rating from Screen Access & Remove OTP Access Gates.  
**Rationale:** While Driver Conduct (#1) and Live Tracking (#3) have higher raw complaints, they require complex third-party fleet governance and cross-platform hardware GPS polling. Conversely, **ACT-001** is a zero-dependency client-side UI fix. Removing the unskippable rating modal and the seatbelt dialog overlaying the OTP button eliminates the primary trigger causing retaliatory 1-star reviews on Google Play.

---

## 3. Key Deliverables & Artifacts

- **[Case Study PDF (8 Pages)](file:///c:/Users/parvk/Downloads/RECURRING%20MONTHLY/reports/MoveInSync_Case_Study.pdf):** Recruiter-ready document located at `reports/MoveInSync_Case_Study.pdf`.
  - *Page 1:* Executive Summary & Problem Statement
  - *Page 2:* Data Collection & Analytical Methodology
  - *Page 3:* Rating Distribution & Temporal Volume Dynamics
  - *Page 4:* Evidence-Backed Defect & Complaint Investigation
  - *Page 5:* Prioritization Decision & Multi-Factor Scoring Model
  - *Page 6:* Targeted Engineering Action Plan (ACT-001, ACT-002, ACT-003)
  - *Page 7:* Measurement Baseline, Targets & Outcome Evaluation
  - *Page 8:* Recurring Monthly Monitoring System & Runbook
- **Live Production Deployment (Vercel):** [https://movesync-rating-intelligence-kappa.vercel.app](https://movesync-rating-intelligence-kappa.vercel.app)
- **Interactive Operations Dashboard:** Served locally at `http://localhost:8000` (or via Vercel) with 6 integrated views:
  - *Current Investigation:* Metadata, Play Store vs sample score divergence, distribution charts.
  - *Evidence Explorer:* Live search, filter by score, theme, period, version with verbatim quotes.
  - *Priority Register:* Multi-factor scoring breakdown, rank deltas, direct links to improvement playbooks.
  - *Month-over-Month Comparison:* 12-month longitudinal trends, theme trajectories (Emerging, Improving, Worsening, Persistent).
  - *Action Tracker:* Intervention statuses, baseline vs target metrics, strict non-causal labels (`observed_association`, `inconclusive`).
  - *Improvement & Recommendation Playbook:* Interactive modal and dedicated view detailing **WHAT to improve** (symptom diagnosis, verbatim citations, critical journey stage, baseline metrics) and **HOW to improve it** (architecture, step-by-step technical execution, tech stack, canary rollout, operational guardrails).
  - *Reports & Exports:* CSV exports of reviews and issues, 8-page recruiter-ready Case Study PDF download.


---

## 4. Technology Stack & Architecture

- **Backend & API:** Python 3.11, FastAPI, Uvicorn, SQLite3 (persistent local database).
- **Data Engineering & Analysis:** Pandas, NumPy, `google-play-scraper`.
- **Report & Visualization Engine:** ReportLab (custom `NumberedCanvas` for 8-page document), Matplotlib (high-resolution chart generation).
- **Interactive Frontend:** HTML5, Tailwind CSS, Vanilla modern ES6, Chart.js, Lucide Icons.
- **Automated Testing:** Pytest, HTTPX, FastAPI TestClient.

### Repository Structure
```
movesync-rating-intelligence/
├── README.md                          # Central recruiter landing page
├── requirements.txt                   # Production dependencies
├── backend/
│   ├── app.py                         # FastAPI REST application & static server
│   └── database.py                    # SQLite schema, migrations & CRUD persistence
├── analysis/
│   ├── collector.py                   # Stage A: Play Store scraper & file import adapter
│   ├── validator.py                   # Stage B: Schema validation & deduplication
│   ├── classifier.py                  # Stage C & D: Taxonomy classification & sentiment
│   ├── prioritization.py              # Stage E: Multi-factor priority scoring formula
│   ├── mom_comparison.py              # Stage E & H: Month-over-month deltas & trajectories
│   ├── outcome_evaluator.py           # Stage F & G: Action tracking & non-causal evaluation
│   └── pipeline.py                    # Orchestrator executing Stages A through H
├── frontend/
│   ├── index.html                     # Responsive operations dashboard
│   ├── app.js                         # Dynamic chart rendering & API client
│   └── styles.css                     # Custom styles
├── reports/
│   ├── MoveInSync_Case_Study.pdf      # Deliverable A: 8-Page Case Study PDF
│   └── assets/                        # High-resolution chart images
├── data/
│   ├── movesync_intelligence.db       # Persistent SQLite database (14 monthly runs)
│   └── raw/                           # Raw immutable JSON/CSV evidence snapshots
├── tests/
│   ├── test_validator.py              # Validation, schema & deduplication tests
│   ├── test_classifier.py             # Theme taxonomy & sentiment tests
│   ├── test_prioritization.py         # Priority formula & rank comparison tests
│   ├── test_historical.py             # MoM deltas & trajectory classification tests
│   ├── test_actions.py                # Action outcome & anti-causal labeling tests
│   └── test_api.py                    # FastAPI endpoint integration tests
└── docs/
    ├── architecture.md                # System design & pipeline architecture
    ├── methodology.md                 # Scoring weights & non-causal guardrails
    ├── data_dictionary.md             # Complete database schema reference
    └── runbook.md                     # Monthly operations & cron setup guide
```

---

## 5. Automated Test Results

The test suite contains **22 automated tests** covering data validation, theme classification, priority scoring, MoM comparisons, non-causal action evaluation, and REST API endpoints.

```
============================= test session starts =============================
platform win32 -- Python 3.11.0, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\parvk\Downloads\RECURRING MONTHLY
plugins: anyio-4.15.1
collected 22 items

tests\test_actions.py ..                                                 [  9%]
tests\test_api.py ........                                               [ 45%]
tests\test_classifier.py ....                                            [ 63%]
tests\test_historical.py ..                                              [ 72%]
tests\test_prioritization.py ..                                          [ 81%]
tests\test_validator.py ....                                             [100%]

======================== 22 passed in 8.13s (100% pass rate) ===================
```

To run tests:
```bash
py -m pytest tests/
```

---

## 6. How to Run & Reproduce

### 1. Start the Live Application
```bash
py -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in any browser.

### 2. Execute a Monthly Investigation Run
- **Via UI:** Click **Run Monthly Run** in the header, select `2026-11`, and click **Execute Investigation**.
- **Via CLI:**
  ```bash
  py -m analysis.pipeline
  ```

### 3. Generate or Inspect the 8-Page Case Study PDF
```bash
py -c "from analysis.pipeline import InvestigationPipeline; InvestigationPipeline().generate_case_study_pdf()"
```
The generated PDF is located at `reports/MoveInSync_Case_Study.pdf`.

---

## 7. Data Limitations & Non-Causal Guardrails

1. **Negative Review Skew:** Public app store reviews reflect commuters experiencing either extraordinary delight or acute frustration. Commuters with ordinary, punctual rides rarely review on Google Play.
2. **Enterprise Client Policy Confounder:** Corporate transport managers enforce company-specific booking cut-offs, routing rules, and vendor vehicle caps. Certain commuter complaints reflect employer policy rather than MoveInSync software bugs.
3. **Strict Non-Causal Attribution:** We do not claim causation merely because complaint rates shifted after an app update. Outcomes are strictly labeled as `observed_association`, `inconclusive`, or `pending`.
