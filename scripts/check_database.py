from sqlalchemy import func, select
from config import make_engine, make_session_factory
from db.models import PipelineRun, Transaction, QuarantinedRecord

if __name__ == "__main__":
    engine = make_engine()
    with make_session_factory(engine)() as session:
        print("pipeline_runs:", session.scalar(select(func.count()).select_from(PipelineRun)))
        print("transactions:", session.scalar(select(func.count()).select_from(Transaction)))
        print("quarantined_records:", session.scalar(select(func.count()).select_from(QuarantinedRecord)))
        for run in session.scalars(select(PipelineRun).order_by(PipelineRun.id)):
            print(f"run_id={run.id} status={run.status} total={run.total_rows} valid={run.valid_rows} quarantined={run.quarantined_rows}")
