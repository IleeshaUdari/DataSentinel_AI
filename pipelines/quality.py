
from collections import Counter

from sqlalchemy import select

from db.models import (
    DataQualityReport,
    PipelineRun,
    QuarantinedRecord,
    Transaction,
)


def percentage(numerator, denominator):
    if denominator == 0:
        return 100.0
    return round(100.0 * numerator / denominator, 2)


def calculate_quality_report(session, run_id):
    run = session.get(PipelineRun, run_id)

    if run is None:
        raise ValueError(f"Pipeline run {run_id} not found")

    transactions = session.scalars(
        select(Transaction).where(
            Transaction.pipeline_run_id == run_id
        )
    ).all()

    quarantined = session.scalars(
        select(QuarantinedRecord).where(
            QuarantinedRecord.pipeline_run_id == run_id
        )
    ).all()

    total = run.total_rows
    valid = len(transactions)
    invalid = len(quarantined)

    if total != valid + invalid:
        raise ValueError(
            "Pipeline counts do not match stored records"
        )

    required_fields = (
        "transaction_id",
        "customer_id",
        "product_id",
        "transaction_date",
        "quantity",
        "unit_price",
        "currency",
        "country",
    )

    missing_cells = 0
    reason_counts = Counter()

    for record in quarantined:
        raw = record.raw_record

        for field in required_fields:
            if not str(raw.get(field, "")).strip():
                missing_cells += 1

        reason_counts.update(record.reason_codes)

    total_cells = total * len(required_fields)

    completeness = percentage(
        total_cells - missing_cells,
        total_cells,
    )

    validity = percentage(valid, total)

    # Measure duplicate external IDs across valid records.
    ids = [item.transaction_id for item in transactions]
    unique_ids = len(set(ids))
    uniqueness = percentage(unique_ids, len(ids))

    # Consistency here measures allowed currency-country
    # combinations. These are configurable business rules.
    allowed_pairs = {
        ("USD", "US"),
        ("GBP", "GB"),
        ("EUR", "DE"),
        ("SGD", "SG"),
        ("LKR", "LK"),
    }

    consistent = sum(
        (item.currency, item.country) in allowed_pairs
        for item in transactions
    )

    consistency = percentage(consistent, len(transactions))

    overall = round(
        0.25 * completeness
        + 0.35 * validity
        + 0.20 * uniqueness
        + 0.20 * consistency,
        2,
    )

    metrics = {
        "total_rows": total,
        "valid_rows": valid,
        "quarantined_rows": invalid,
        "missing_cells": missing_cells,
        "validation_reasons": dict(reason_counts),
        "unique_transaction_ids": unique_ids,
        "consistent_currency_country_rows": consistent,
        "scoring_weights": {
            "completeness": 0.25,
            "validity": 0.35,
            "uniqueness": 0.20,
            "consistency": 0.20,
        },
    }

    report = session.scalar(
        select(DataQualityReport).where(
            DataQualityReport.pipeline_run_id == run_id
        )
    )

    if report is None:
        report = DataQualityReport(pipeline_run_id=run_id)
        session.add(report)

    report.total_rows = total
    report.valid_rows = valid
    report.quarantined_rows = invalid
    report.completeness_score = completeness
    report.validity_score = validity
    report.uniqueness_score = uniqueness
    report.consistency_score = consistency
    report.overall_score = overall
    report.metrics = metrics

    session.flush()
    return report
