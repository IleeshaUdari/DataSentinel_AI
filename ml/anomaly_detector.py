
import numpy as np

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


FEATURE_NAMES = (
    "log_quantity",
    "log_unit_price",
    "log_total_amount",
)


def extract_features(transactions):
    features = []

    for transaction in transactions:
        quantity = float(transaction.quantity)
        unit_price = transaction.unit_price_cents / 100.0
        total_amount = quantity * unit_price

        features.append([
            np.log1p(quantity),
            np.log1p(unit_price),
            np.log1p(total_amount),
        ])

    if not features:
        return np.empty((0, 3), dtype=float)

    return np.asarray(features, dtype=float)


def detect_anomalies(
    transactions,
    contamination=0.03,
    random_state=42,
):
    if not 0 < contamination <= 0.5:
        raise ValueError(
            "contamination must be greater than 0 and at most 0.5"
        )

    if len(transactions) < 20:
        raise ValueError(
            "At least 20 transactions are required"
        )

    features = extract_features(transactions)

    scaler = StandardScaler()
    scaled = scaler.fit_transform(features)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=random_state,
        n_jobs=1,
    )

    predictions = model.fit_predict(scaled)

    # Lower decision_function values are more anomalous.
    decision_scores = model.decision_function(scaled)

    results = []

    for transaction, prediction, score in zip(
        transactions,
        predictions,
        decision_scores,
    ):
        results.append({
            "transaction_id": transaction.id,
            "is_anomaly": bool(prediction == -1),
            "anomaly_score": float(-score),
        })

    return results
