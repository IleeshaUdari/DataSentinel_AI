
from types import SimpleNamespace

import numpy as np
import pytest

from ml.anomaly_detector import (
    detect_anomalies,
    extract_features,
)
from pipelines.incidents import (
    classify_severity,
    explain_anomaly,
)
from pipelines.quality import percentage


def make_transaction(index, quantity=2, price=1500):
    return SimpleNamespace(
        id=index,
        transaction_id=f"TXN-{index}",
        quantity=quantity,
        unit_price_cents=price,
        currency="USD",
    )


def test_percentage_normal():
    assert percentage(98, 100) == 98.0


def test_percentage_empty():
    assert percentage(0, 0) == 100.0


def test_extract_features_shape():
    transactions = [
        make_transaction(1),
        make_transaction(2),
    ]

    features = extract_features(transactions)

    assert features.shape == (2, 3)
    assert np.isfinite(features).all()


def test_extract_features_empty():
    features = extract_features([])
    assert features.shape == (0, 3)


def test_anomaly_detector_output_count():
    transactions = [
        make_transaction(i, quantity=(i % 10) + 1)
        for i in range(1, 101)
    ]

    results = detect_anomalies(transactions)

    assert len(results) == 100
    assert all("anomaly_score" in r for r in results)
    assert all(isinstance(r["is_anomaly"], bool) for r in results)


def test_anomaly_detector_reproducible():
    transactions = [
        make_transaction(i, quantity=(i % 15) + 1)
        for i in range(1, 101)
    ]

    first = detect_anomalies(transactions)
    second = detect_anomalies(transactions)

    assert first == second


def test_anomaly_detector_minimum_rows():
    transactions = [make_transaction(1)]

    with pytest.raises(ValueError):
        detect_anomalies(transactions)


def test_anomaly_detector_invalid_contamination():
    transactions = [make_transaction(i) for i in range(20)]

    with pytest.raises(ValueError):
        detect_anomalies(transactions, contamination=0.8)


@pytest.mark.parametrize(
    "score,expected",
    [
        (0.20, "critical"),
        (0.10, "high"),
        (0.05, "medium"),
        (0.01, "low"),
    ],
)
def test_severity(score, expected):
    assert classify_severity(score) == expected


def test_incident_explanation():
    transaction = make_transaction(
        1,
        quantity=500,
        price=2000000,
    )

    incident = explain_anomaly(transaction, 0.20)

    assert incident["severity"] == "critical"
    assert "quantity" in incident["description"]
    assert incident["recommended_action"]
