
from sqlalchemy import func, select

from config import make_engine, make_session_factory
from db.models import (
    AnomalyResult,
    DataIncident,
    DataQualityReport,
)


def main():
    engine = make_engine()
    session_factory = make_session_factory(engine)

    with session_factory() as session:
        reports = session.scalar(
            select(func.count(DataQualityReport.id))
        )

        predictions = session.scalar(
            select(func.count(AnomalyResult.id))
        )

        anomalies = session.scalar(
            select(func.count(AnomalyResult.id)).where(
                AnomalyResult.is_anomaly.is_(True)
            )
        )

        incidents = session.scalar(
            select(func.count(DataIncident.id))
        )

        print(f"quality_reports: {reports}")
        print(f"anomaly_results: {predictions}")
        print(f"anomalies_detected: {anomalies}")
        print(f"data_incidents: {incidents}")

        report = session.scalar(
            select(DataQualityReport)
            .order_by(DataQualityReport.id.desc())
            .limit(1)
        )

        if report:
            print(
                f"latest_quality_score: {report.overall_score}"
            )


if __name__ == "__main__":
    main()
