import re
from datetime import datetime
from typing import Any

def safe_parse_int(value: str) -> int | None:
    """
    Safe parse int, in internal test sometimes gemini returned quantities
    like '123 apples' a problem for numeric fields in the db,
    so hopefully this and the other numeric function mitigates that
    """
    match = re.match(r"\s*(-?\d+)", str(value))
    return int(match.group(1)) if match else None

def safe_parse_float(value: str) -> float | None:
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else None

def safe_parse_date(date_str: str) -> datetime | None:
    """
    Try to parse a date returned by gemini, if not possible simply ignore the field
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None

def safe_parse_str(value: Any):
    try:
        return str(value)
    except Exception:
        "this should happen almost never"
        return ''