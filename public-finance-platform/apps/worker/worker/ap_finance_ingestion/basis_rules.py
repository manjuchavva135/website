from __future__ import annotations


def map_basis_tag(label: str, source_family: str) -> str:
    text = f"{label} {source_family}".lower()
    if any(token in text for token in {"accounts", "actuals", "actual"}):
        return "actual"
    if any(token in text for token in {"budget estimate", "be"}):
        return "budget_estimate"
    if "revised estimate" in text:
        return "revised_estimate"
    if any(token in text for token in {"projection", "projected"}):
        return "projection"
    if any(token in text for token in {"quarter", "q1", "q2", "q3", "q4"}):
        return "quarter_actual"
    return "actual"
