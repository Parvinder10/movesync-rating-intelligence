# Monthly Operations Runbook

Instructions for Forward Deployed Engineers and Product Analysts to operate and maintain the MoveSync Rating Intelligence System.

---

## 1. Quick Start & Local Execution

### Prerequisites
- Python 3.11+
- SQLite3 (included with Python standard library)

### Installing Dependencies
```bash
py -m pip install -r requirements.txt
```

### Starting the Operations Dashboard & Backend Service
```bash
py -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to `http://localhost:8000` to open the interactive dashboard.

---

## 2. Executing a Monthly Investigation

### Option A: Via Dashboard Interface (Recommended)
1. Open the dashboard at `http://localhost:8000`.
2. Click the blue **Run Monthly Run** button in the header.
3. Select the target period (e.g. `2026-11`).
4. (Optional) Check "Fetch fresh live reviews from Google Play Store" to scrape new reviews.
5. Click **Execute Investigation**.
6. The dashboard will automatically update all charts, issue rankings, MoM deltas, and the 8-page PDF deliverable.

### Option B: Via Command Line Interface (CLI)
To run an investigation for the latest period or backfill historical months:
```bash
# Execute collection and all historical period investigations
py -m analysis.pipeline
```

To run a specific monthly period programmatically:
```python
from analysis.pipeline import InvestigationPipeline

pipeline = InvestigationPipeline()
result = pipeline.run_investigation_for_period("2026-11")
print("Investigation completed for 2026-11. Top issue:", result["run"]["top_issue_theme"])
```

---

## 3. Recurring Scheduled Execution

### Setting up a Scheduled Monthly Job (Windows Task Scheduler)
To execute the pipeline automatically on the 1st of every month at 02:00 AM:
```powershell
$action = New-ScheduledTaskAction -Execute "py.exe" -Argument "-m analysis.pipeline" -WorkingDirectory "C:\Users\parvk\Downloads\RECURRING MONTHLY"
$trigger = New-ScheduledTaskTrigger -Monthly -DaysOfWeek Monday -At 02:00am
Register-ScheduledTask -TaskName "MoveSyncMonthlyInvestigation" -Action $action -Trigger $trigger -Description "Monthly Play Store investigation and case study generation for MoveInSync"
```

### Setting up a Scheduled Monthly Job (Linux Cron)
```bash
# Run on the 1st of every month at 03:00 AM
0 3 1 * * cd /path/to/movesync-rating-intelligence && python3 -m analysis.pipeline >> /var/log/movesync_pipeline.log 2>&1
```

---

## 4. Handling Missing Data & Edge Cases

1. **Google Play Scraper Rate-Limiting or Offline:**
   - The pipeline will log a warning and fall back to existing verified records in `data/movesync_intelligence.db`.
   - Alternatively, use the file import workflow:
     ```python
     pipeline.collect_and_ingest(import_file="data/raw/reviews_manual_export.json")
     ```
2. **Zero Reviews in a Month:**
   - The pipeline explicitly marks the period as `incomplete` in `investigation_runs`, preserving failure metadata without corrupting earlier runs.
3. **Idempotent Reruns:**
   - Rerunning a month will update `investigation_runs` and `issue_snapshots` without creating duplicate reviews, thanks to SQLite primary key deduplication on `review_id`.
