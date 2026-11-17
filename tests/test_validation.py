from pipelines.validation import validate_record

GOOD = {"transaction_id":"TXN-1", "customer_id":"CUS-1", "product_id":"SKU-1", "transaction_date":"2026-01-15", "quantity":"2", "unit_price":"12.50", "currency":"USD", "country":"US"}


def test_valid_record():
    data, errors = validate_record(GOOD)
    assert errors == []
    assert data["unit_price_cents"] == 1250
    assert data["quantity"] == 2


def test_missing_customer():
    data, errors = validate_record({**GOOD, "customer_id":""})
    assert data is None
    assert "MISSING_CUSTOMER_ID" in errors


def test_negative_quantity():
    _, errors = validate_record({**GOOD, "quantity":"-1"})
    assert "INVALID_QUANTITY" in errors


def test_invalid_currency():
    _, errors = validate_record({**GOOD, "currency":"XYZ"})
    assert "INVALID_CURRENCY" in errors


def test_invalid_date():
    _, errors = validate_record({**GOOD, "transaction_date":"2026-13-45"})
    assert "INVALID_TRANSACTION_DATE" in errors


def test_nonfinite_price():
    _, errors = validate_record({**GOOD, "unit_price":"NaN"})
    assert "INVALID_UNIT_PRICE" in errors


def test_excessive_price_precision():
    _, errors = validate_record({**GOOD, "unit_price":"1.001"})
    assert "INVALID_UNIT_PRICE" in errors
