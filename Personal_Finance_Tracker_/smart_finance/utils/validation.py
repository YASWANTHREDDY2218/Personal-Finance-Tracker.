import math
from datetime import date

def positive_amount(raw, label="Amount"):
    try:
        amount = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.")
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError(f"{label} must be greater than ₹0.")
    return amount

def valid_date(raw):
    try:
        return date.fromisoformat(raw).isoformat()
    except (TypeError, ValueError):
        raise ValueError("Use a valid date in YYYY-MM-DD format.")
