import csv
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from db.models import Base, PipelineRun, Transaction, QuarantinedRecord
from pipelines.ingestion import ingest_file
from scripts.generate_data import generate, HEADERS


def make_test_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_generated_dataset_and_idempotency(tmp_path):
    factory = make_test_db(tmp_path)
    path = generate(tmp_path / "orders.csv", count=100, seed=42)
    first = ingest_file(factory, path)
    assert first["status"] == "completed"
    assert first["total_rows"] == 100
    assert first["valid_rows"] == 98
    assert first["quarantined_rows"] == 2
    second = ingest_file(factory, path)
    assert second["status"] == "skipped"
    with factory() as session:
        assert session.scalar(select(func.count()).select_from(PipelineRun)) == 1
        assert session.scalar(select(func.count()).select_from(Transaction)) == 98
        assert session.scalar(select(func.count()).select_from(QuarantinedRecord)) == 2


def test_duplicate_ids_in_same_file(tmp_path):
    factory = make_test_db(tmp_path)
    path = tmp_path / "duplicates.csv"
    row = {"transaction_id":"TXN-1", "customer_id":"CUS-1", "product_id":"SKU-1", "transaction_date":"2026-01-01", "quantity":"1", "unit_price":"1.00", "currency":"USD", "country":"US"}
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows([row, row])
    result = ingest_file(factory, path)
    assert result["valid_rows"] == 1
    assert result["quarantined_rows"] == 1


def test_duplicate_ids_across_files(tmp_path):
    factory = make_test_db(tmp_path)
    first = generate(tmp_path / "one.csv", count=100, seed=1)
    second = generate(tmp_path / "two.csv", count=100, seed=2)
    ingest_file(factory, first)
    result = ingest_file(factory, second)
    assert result["valid_rows"] == 2  # IDs rejected in the first file can be accepted in the second
    assert result["quarantined_rows"] == 98


def test_invalid_header_marks_run_failed(tmp_path):
    factory = make_test_db(tmp_path)
    path = tmp_path / "bad.csv"
    path.write_text("bad,columns\na,b\n", encoding="utf-8")
    import pytest
    with pytest.raises(ValueError):
        ingest_file(factory, path)
    with factory() as session:
        run = session.scalar(select(PipelineRun))
        assert run.status == "failed"
        assert session.scalar(select(func.count()).select_from(Transaction)) == 0
