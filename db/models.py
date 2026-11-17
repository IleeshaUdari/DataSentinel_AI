from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, JSON, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="processing")
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quarantined_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("source_name", "transaction_id", name="uq_source_transaction"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pipeline_run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id"), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    transaction_id: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(64), nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), nullable=False)
    transaction_date: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)


class QuarantinedRecord(Base):
    __tablename__ = "quarantined_records"
    __table_args__ = (UniqueConstraint("pipeline_run_id", "row_number", name="uq_run_row"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pipeline_run_id: Mapped[int] = mapped_column(ForeignKey("pipeline_runs.id"), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_codes: Mapped[list] = mapped_column(JSON, nullable=False)
    raw_record: Mapped[dict] = mapped_column(JSON, nullable=False)


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id"),
        unique=True,
        nullable=False,
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    quarantined_rows: Mapped[int] = mapped_column(Integer, nullable=False)

    completeness_score: Mapped[float] = mapped_column(Float, nullable=False)
    validity_score: Mapped[float] = mapped_column(Float, nullable=False)
    uniqueness_score: Mapped[float] = mapped_column(Float, nullable=False)
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)

    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class AnomalyResult(Base):
    __tablename__ = "anomaly_results"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_run_id",
            "transaction_id",
            name="uq_anomaly_run_transaction",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id"),
        nullable=False,
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
    )
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(nullable=False)
    model_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="IsolationForest",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )


class DataIncident(Base):
    __tablename__ = "data_incidents"
    __table_args__ = (
        UniqueConstraint(
            "pipeline_run_id",
            "transaction_id",
            name="uq_incident_run_transaction",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id"),
        nullable=False,
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.id"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="open",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
