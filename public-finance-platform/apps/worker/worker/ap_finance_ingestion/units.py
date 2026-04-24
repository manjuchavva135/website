from __future__ import annotations

from decimal import Decimal
import re


def parse_number(value: str) -> Decimal | None:
    cleaned = value.replace(",", "").strip()
    if not cleaned:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None
    return Decimal(match.group(0))


def normalize_to_crore(amount: Decimal, unit_label: str) -> Decimal:
    unit = unit_label.lower()
    if "lakh" in unit or "lac" in unit:
        return (amount / Decimal("100")).quantize(Decimal("0.0001"))
    if "crore" in unit or "cr" in unit:
        return amount
    if "million" in unit:
        return (amount / Decimal("10")).quantize(Decimal("0.0001"))
    return amount


def detect_unit_label(text: str, fallback: str = "INR crore") -> str:
    lowered = text.lower()
    if "lakh" in lowered or "lac" in lowered:
        return "INR lakh"
    if "crore" in lowered or "cr" in lowered:
        return "INR crore"
    if "million" in lowered:
        return "INR million"
    return fallback
