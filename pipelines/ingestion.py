import csv
import hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from db.models import PipelineRun, Transaction, QuarantinedRecord
from pipelines.validation import REQUIRED, validate_record


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_file(session_factory, csv_path, source_name="retail_orders"):
    path = Path(csv_path)
    digest = sha256_file(path)
    # Run is committed separately so failures remain visible in pipeline_runs.
    with session_factory() as session:
        existing = session.scalar(select(PipelineRun).where(PipelineRun.file_sha256 == digest))
        if existing:
            if existing.status == "completed":
                return {"status": "skipped", "run_id": existing.id, "reason": "file already processed", "valid_rows": existing.valid_rows, "quarantined_rows": existing.quarantined_rows}
            raise RuntimeError(f"File already registered as run {existing.id} with status {existing.status}; investigate before retrying")
        run = PipelineRun(source_name=source_name, file_sha256=digest, status="processing")
        session.add(run)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise RuntimeError("This file is already being processed by another worker") from None
        run_id = run.id

    total = valid = quarantined = 0
    seen_ids = set()
    try:
        with session_factory() as session:
            with path.open("r", newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or set(reader.fieldnames) != set(REQUIRED):
                    raise ValueError(f"CSV must have exactly these unique columns: {', '.join(REQUIRED)}")
                for line_number, row in enumerate(reader, start=2):
                    total += 1
                    cleaned, errors = validate_record(row)
                    # Detect duplicates in this batch, including duplicates of invalid records with an ID.
                    transaction_id = str(row.get("transaction_id") or "").strip()
                    if transaction_id:
                        if transaction_id in seen_ids:
                            errors.append("DUPLICATE_TRANSACTION_ID_IN_FILE")
                        else:
                            seen_ids.add(transaction_id)
                    if not errors and session.scalar(select(Transaction.id).where(Transaction.source_name == source_name, Transaction.transaction_id == cleaned["transaction_id"])) is not None:
                        errors.append("DUPLICATE_TRANSACTION_ID_IN_DATABASE")
                    if errors:
                        session.add(QuarantinedRecord(pipeline_run_id=run_id, row_number=line_number, reason_codes=sorted(set(errors)), raw_record={k: v for k, v in row.items()}))
                        quarantined += 1
                    else:
                        session.add(Transaction(pipeline_run_id=run_id, source_name=source_name, **cleaned))
                        valid += 1
                    # Flush regularly to limit ORM pending object memory and enforce constraints.
                    if total % 500 == 0:
                        session.flush()
            run = session.get(PipelineRun, run_id)
            run.total_rows = total
            run.valid_rows = valid
            run.quarantined_rows = quarantined
            run.status = "completed"
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
    except Exception as exc:
        with session_factory() as session:
            run = session.get(PipelineRun, run_id)
            run.status = "failed"
            run.error_message = str(exc)[:2000]
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
        raise
    return {"status": "completed", "run_id": run_id, "total_rows": total, "valid_rows": valid, "quarantined_rows": quarantined}
