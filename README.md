# EduTrack AI — runnable end-to-end analytics challenge

Fully synthetic, fixed-seed learning analytics. Python 3.10+ required. No external data, API keys or paid services. Frontend is standalone HTML/JavaScript with Chart.js via CDN (offline fallback displays JSON).

## Quick start (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.generate --out data/starter
python -m uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000 and API docs http://127.0.0.1:8000/docs .

## macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m backend.generate --out data/starter
python -m uvicorn backend.main:app --reload
```

## Full-scale generation (takes time and several hundred MB of disk)

```bash
python -m backend.generate --out data/full --learners 20000 --courses 500 --enrollments 100000 --events 2000000 --seed 20261022
```

To view full data, set EDUTRACK_DB to the absolute path of `data/full/edutrack.db` before launching uvicorn.

## Reproducibility

```bash
python -m backend.generate --out data/run1 --learners 30 --courses 4 --enrollments 60 --events 400
python -m backend.generate --out data/run2 --learners 30 --courses 4 --enrollments 60 --events 400
```

Compare `manifest.json` sha256 objects. Generated CSVs are deterministic and stable. Test: `python -m unittest discover -s tests`.

## Data model and rules

All entity definitions, keys and constraints are in `data/starter/schema.sql` (also exported during generation). One learner has many enrollments, one course has many enrollments, content items, assessments and cohorts. Enrollment is the learner-course bridge, with uniqueness on the pair. One enrollment has many activity events and attempts. An activity event may have a null enrollment for a deliberately labelled unenrolled-activity anomaly. Each enrollment has one current course outcome snapshot; the event and attempt histories are append-only.

`event_time` and `received_at` are UTC ISO-8601 timestamps. Offline sync delays ingestion 48 hours. Event deduplication uses `source_event_key`; flagged duplicates are excluded. Weekly active engagement counts distinct learners/enrollments with valid events in a UTC week. Cohort completion rate = completed enrollments / all enrollments in cohort; compare cohorts at the common synthetic day-60 snapshot. Completion requires 3 distinct content items with `complete` events and at least one passing assessment (score >= 60). Repeated attempts remain in history.

`ground_truth.csv` is a separate evaluation output and must not be supplied as input features. Labelled anomalies include duplicate event, unenrolled activity, timezone shift, and premature completion probes. Premature completion labels refer to rejection test cases, not to deliberately incorrect outcome rows.

## Limitations

This is a functional reference implementation rather than a production-ready service. It uses SQLite and an HTML/JS dashboard for zero-build setup. No authentication/authorization is included. The completion outcome is a deterministic snapshot, not a full event-sourced state-transition ledger. For production, add access controls, migrations, incremental aggregation, partitioned event storage and explicit outcome transition records.
