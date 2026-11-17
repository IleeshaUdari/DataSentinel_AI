
import argparse
import json

from sqlalchemy import func, select

from config import make_engine, make_session_factory
from db.models import (
    AnomalyResult,
    Base,
    DataIncident,
    DataQualityReport,
    PipelineRun,
    Transaction,
)
from ml.anomaly_detector import detect_anomalies
from pipelines.incidents import explain_anomaly
from pipelines.quality import calculate_quality_report


def run_intelligence(run_id):
    engine = make_engine()

    # Add only missing Day 2 tables.
    # Existing Day 1 tables and data remain untouched.
    Base.metadata.create_all(engine)

    session_factory = make_session_factory(engine)

    with session_factory() as session:
        run = session.get(PipelineRun, run_id)

        if run is None:
            raise ValueError(f"Pipeline run {run_id} not found")

        if run.status != "completed":
            raise ValueError(
                f"Pipeline run {run_id} is not completed"
            )

        transactions = session.scalars(
            select(Transaction)
            .where(Transaction.pipeline_run_id == run_id)
            .order_by(Transaction.id)
        ).all()

        if len(transactions) < 20:
            raise ValueError(
                "At least 20 valid transactions required"
            )

        existing_count = session.scalar(
            select(func.count(AnomalyResult.id)).where(
                AnomalyResult.pipeline_run_id == run_id
            )
        )

        existing_report = session.scalar(
            select(DataQualityReport).where(
                DataQualityReport.pipeline_run_id == run_id
            )
        )

        if existing_count == len(transactions) and existing_report:
            incidents = session.scalar(
                select(func.count(DataIncident.id)).where(
                    DataIncident.pipeline_run_id == run_id
                )
            )

            return {
                "status": "skipped",
                "reason": "intelligence already processed",
                "run_id": run_id,
                "quality_score": existing_report.overall_score,
                "transactions_scored": existing_count,
                "incidents": incidents,
            }

        if existing_count > 0:
            raise RuntimeError(
                "Partial anomaly results exist. "
                "Manual recovery is required."
            )

        report = calculate_quality_report(session, run_id)

        predictions = detect_anomalies(transactions)

        transaction_map = {
            transaction.id: transaction
            for transaction in transactions
        }

        anomaly_count = 0
        severity_counts = {
            "critical": 0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }

        for prediction in predictions:
            transaction_id = prediction["transaction_id"]
            score = prediction["anomaly_score"]
            is_anomaly = prediction["is_anomaly"]

            session.add(
                AnomalyResult(
                    pipeline_run_id=run_id,
                    transaction_id=transaction_id,
                    anomaly_score=score,
                    is_anomaly=is_anomaly,
                    model_name="IsolationForest",
                )
            )

            if not is_anomaly:
                continue

            anomaly_count += 1

            transaction = transaction_map[transaction_id]
            explanation = explain_anomaly(transaction, score)

            severity = explanation["severity"]
            severity_counts[severity] += 1

            session.add(
                DataIncident(
                    pipeline_run_id=run_id,
                    transaction_id=transaction_id,
                    severity=severity,
                    title=explanation["title"],
                    description=explanation["description"],
                    recommended_action=explanation[
                        "recommended_action"
                    ],
                    status="open",
                )
            )

        result = {
            "status": "completed",
            "run_id": run_id,
            "quality_score": report.overall_score,
            "quality_metrics": {
                "completeness": report.completeness_score,
                "validity": report.validity_score,
                "uniqueness": report.uniqueness_score,
                "consistency": report.consistency_score,
            },
            "transactions_scored": len(predictions),
            "anomalies_detected": anomaly_count,
            "incidents_created": anomaly_count,
            "severity_breakdown": severity_counts,
        }

        # All inserts succeed or roll back together.
        session.commit()

        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", type=int, default=1)
    args = parser.parse_args()

    result = run_intelligence(args.run_id)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
