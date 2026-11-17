
def classify_severity(anomaly_score):
    if anomaly_score >= 0.15:
        return "critical"
    if anomaly_score >= 0.08:
        return "high"
    if anomaly_score >= 0.03:
        return "medium"
    return "low"


def explain_anomaly(transaction, anomaly_score):
    quantity = transaction.quantity
    unit_price = transaction.unit_price_cents / 100.0
    total_amount = quantity * unit_price

    observations = []

    if quantity >= 100:
        observations.append("unusually large purchase quantity")

    if unit_price >= 10000:
        observations.append("high unit price")

    if total_amount >= 50000:
        observations.append("high transaction value")

    if not observations:
        observations.append(
            "unusual combination of numerical transaction features"
        )

    severity = classify_severity(anomaly_score)

    return {
        "severity": severity,
        "title": f"Unusual transaction: {transaction.transaction_id}",
        "description": (
            f"Isolation Forest flagged this transaction. "
            f"Observed patterns: {', '.join(observations)}. "
            f"Quantity={quantity}, unit_price={unit_price:.2f} "
            f"{transaction.currency}, "
            f"total={total_amount:.2f} {transaction.currency}. "
            f"Anomaly score={anomaly_score:.4f}."
        ),
        "recommended_action": (
            "Review the transaction against historical customer "
            "and product behavior. Verify pricing and quantity "
            "before escalating to a human investigator."
        ),
    }
