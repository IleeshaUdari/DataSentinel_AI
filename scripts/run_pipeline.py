import argparse
import json
from config import make_engine, make_session_factory
from db.init_db import init_db
from pipelines.ingestion import ingest_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="data/raw/retail_transactions.csv")
    parser.add_argument("--source", default="retail_orders")
    args = parser.parse_args()
    engine = make_engine()
    init_db(engine)
    result = ingest_file(make_session_factory(engine), args.file, args.source)
    print(json.dumps(result, indent=2))
