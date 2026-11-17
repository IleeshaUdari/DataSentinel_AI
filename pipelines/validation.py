import re
from datetime import date
from decimal import Decimal, InvalidOperation

REQUIRED = ("transaction_id", "customer_id", "product_id", "transaction_date", "quantity", "unit_price", "currency", "country")
CURRENCIES = {"USD", "EUR", "GBP", "SGD", "LKR"}
COUNTRIES = {"US", "GB", "DE", "SG", "LK"}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_record(row):
    errors = []
    cleaned = {}
    for field in REQUIRED:
        if not str(row.get(field, "")).strip():
            errors.append(f"MISSING_{field.upper()}")
    if errors:
        return None, errors

    for field in ("transaction_id", "customer_id", "product_id"):
        value = row[field].strip()
        if not ID_PATTERN.fullmatch(value):
            errors.append(f"INVALID_{field.upper()}")
        cleaned[field] = value

    try:
        parsed_date = date.fromisoformat(row["transaction_date"].strip())
        cleaned["transaction_date"] = parsed_date.isoformat()
    except ValueError:
        errors.append("INVALID_TRANSACTION_DATE")

    try:
        raw_quantity = row["quantity"].strip()
        if not re.fullmatch(r"[+-]?\d+", raw_quantity):
            raise ValueError()
        quantity = int(raw_quantity)
        if not 1 <= quantity <= 1000:
            raise ValueError()
        cleaned["quantity"] = quantity
    except ValueError:
        errors.append("INVALID_QUANTITY")

    try:
        amount = Decimal(row["unit_price"].strip())
        if not amount.is_finite() or not (Decimal("0.01") <= amount <= Decimal("100000.00")):
            raise ValueError()
        if amount.as_tuple().exponent < -2:
            raise ValueError()
        cleaned["unit_price_cents"] = int(amount * 100)
    except (InvalidOperation, ValueError):
        errors.append("INVALID_UNIT_PRICE")

    cleaned["currency"] = row["currency"].strip().upper()
    if cleaned["currency"] not in CURRENCIES:
        errors.append("INVALID_CURRENCY")
    cleaned["country"] = row["country"].strip().upper()
    if cleaned["country"] not in COUNTRIES:
        errors.append("INVALID_COUNTRY")
    return (cleaned, []) if not errors else (None, errors)
