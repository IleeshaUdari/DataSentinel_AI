import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

HEADERS = ["transaction_id", "customer_id", "product_id", "transaction_date", "quantity", "unit_price", "currency", "country"]


def generate(path, count=10000, seed=42):
    if count < 10:
        raise ValueError("count must be at least 10")
    rng = random.Random(seed)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for i in range(1, count + 1):
        rows.append({
            "transaction_id": f"TXN-{i:07d}",
            "customer_id": f"CUS-{rng.randint(1, 2000):05d}",
            "product_id": f"SKU-{rng.randint(1, 300):04d}",
            "transaction_date": (date(2026, 1, 1) + timedelta(days=rng.randint(0, 180))).isoformat(),
            "quantity": str(rng.randint(1, 12)),
            "unit_price": f"{rng.randint(100, 100000) / 100:.2f}",
            "currency": rng.choice(["USD", "EUR", "GBP", "SGD", "LKR"]),
            "country": rng.choice(["US", "GB", "DE", "SG", "LK"]),
        })
    # Inject deterministic invalid records: 2% of the dataset, each in a distinct row.
    indices = rng.sample(range(count), count // 50)
    corruptions = [
        ("customer_id", ""),
        ("quantity", "-3"),
        ("unit_price", "-10.00"),
        ("currency", "XYZ"),
        ("transaction_date", "2026-99-99"),
        ("transaction_id", ""),
        ("country", "ZZ"),
        ("unit_price", "not-a-number"),
    ]
    for j, index in enumerate(indices):
        field, value = corruptions[j % len(corruptions)]
        rows[index][field] = value
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {count} rows at {path}; intentionally invalid rows: {len(indices)}")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/raw/retail_transactions.csv")
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.output, args.count, args.seed)
