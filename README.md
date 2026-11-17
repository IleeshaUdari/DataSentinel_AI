# DataSentinel AI — Day 1

Enterprise-style data quality and ingestion MVP with PostgreSQL, Python, quarantine and idempotency.

## Requirements
- Python 3.13 (or 3.12)
- Docker Desktop (Linux containers)

## Setup (PowerShell)
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
docker compose up -d
docker compose ps
python -m db.init_db
python -m scripts.generate_data --count 10000
python -m scripts.run_pipeline
python -m scripts.run_pipeline
python -m scripts.check_database
python -m pytest -q
```

## Expected results
- Generated: 10,000 rows, 200 intentionally invalid
- First ingest: 9,800 valid, 200 quarantined
- Second ingest: skipped (same file SHA-256)
- Database: 1 pipeline run, 9,800 transactions, 200 quarantined rows
- 11 pytest tests pass (7 validation + 4 ingestion)

## Design notes
- **Idempotency**: SHA-256 of file contents uniquely identifies an ingested file, regardless of filename. Existing transaction IDs are also checked per source across batches.
- **Quarantine**: Invalid rows retain their raw content, original CSV line number and reason codes.
- **Atomicity**: All records for a batch are committed together; failed batches roll back records and persist a failed run status.
- **Scope**: This is a sequential local MVP. It does not yet support distributed workers, retrying failed runs, schema migrations, streaming ingestion or authentication.
- **Security**: `.env` and generated CSV files are ignored. The Compose database password is intentionally a local-development credential; never deploy it publicly.
- **Privacy**: All generated data is synthetic.
- **Data**: `unit_price_cents` avoids floating-point currency storage.
- **Future**: Day 2 adds quality metrics and anomaly detection; Day 3 adds FastAPI; Day 4 adds dashboard; Day 5 adds deployment CI and documentation.
