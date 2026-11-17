from config import make_engine
from db.models import Base


def init_db(engine=None):
    engine = engine or make_engine()
    Base.metadata.create_all(engine)
    return engine


if __name__ == "__main__":
    init_db()
    print("Database tables created: pipeline_runs, transactions, quarantined_records")
