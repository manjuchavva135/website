"""Parser for the RBI 'State Finances: A Study of Budgets of 2025-26' statements.

Each PDF in this dataset is one Statement (or Appendix) covering all states
across multiple fiscal years. This parser detects the statement type from
the first-page text, then extracts only the Andhra Pradesh row(s) into
shape-stable record types.

Supported statements:
    Statement 2  : Revenue Receipts / Expenditure / Surplus(-) Deficit(+)
    Statement 13 : Interest Payments (Gross / Net*)
    Statement 16 : Loans from the Centre (Gross / Net*)
    Statement 19 : Total Outstanding Liabilities (annual time series 2008-2026)
    Statement 21 : Market Borrowings (Gross Raised / Repayments)
    Statement 22 : State Government Market Loans — per-instrument outstanding
    Statement 23 : Maturity Profile of Outstanding Securities (year buckets)
    Appendix I   : Revenue Receipts of States — per-item breakdown

All values are converted to ₹ Crore (Appendix I native unit is ₹ Lakh and
is divided by 100).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO

import pdfplumber

# --------------------------------------------------------------------------- #
# Record types. Field names match what manual_upload._save_fiscal_metrics    #
# and _save_debt_positions consume (see worker/tasks/manual_upload.py).       #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class _Provenance:
    page_number: int
    row_number: int | None = None
    row_label: str | None = None
    quoted_text: str | None = None


@dataclass(frozen=True, slots=True)
class ParsedFiscalMetricRecord:
    metric_code: str
    metric_name: str
    metric_group: str
    basis_tag: str
    fiscal_year: str
    period_start: date
    period_end: date
    value_inr_crore: Decimal
    unit: str = "INR crore"
    department_code: str | None = None
    notes: str | None = None
    provenance: _Provenance | None = None
    parser_confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class ParsedDebtPositionRecord:
    instrument_code: str
    instrument_name: str
    issuer_name: str
    as_of_date: date
    basis_tag: str
    outstanding_principal_inr_crore: Decimal
    accrued_interest_inr_crore: Decimal | None = None
    face_value_inr_crore: Decimal | None = None
    market_value_inr_crore: Decimal | None = None
    coupon_rate: Decimal | None = None
    maturity_date: date | None = None
    provenance: _Provenance | None = None
    parser_confidence: float = 1.0


@dataclass(slots=True)
class StateFinancesResult:
    statement_id: str  # 'stmt_2', 'stmt_22', 'appendix_1', etc.
    fiscal_metrics: list[ParsedFiscalMetricRecord] = field(default_factory=list)
    debt_positions: list[ParsedDebtPositionRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #

def parse_state_finances_pdf(payload: bytes, source_url: str = "") -> StateFinancesResult:
    """Detect the statement type and dispatch to the appropriate parser."""
    with pdfplumber.open(BytesIO(payload)) as pdf:
        first_text = pdf.pages[0].extract_text() or ""
        all_pages_text = [page.extract_text() or "" for page in pdf.pages]

    stmt_id = _detect_statement(first_text)
    result = StateFinancesResult(statement_id=stmt_id)

    if stmt_id == "stmt_2":
        _parse_stmt_2(all_pages_text[0], result)
    elif stmt_id == "stmt_13":
        _parse_stmt_13(all_pages_text[0], result)
    elif stmt_id == "stmt_16":
        _parse_stmt_16(all_pages_text[0], result)
    elif stmt_id == "stmt_19":
        _parse_stmt_19(all_pages_text[0], result)
    elif stmt_id == "stmt_21":
        _parse_stmt_21(all_pages_text[0], result)
    elif stmt_id == "stmt_22":
        _parse_stmt_22(all_pages_text, result)
    elif stmt_id == "stmt_23":
        _parse_stmt_23(all_pages_text[0], result)
    elif stmt_id == "appendix_1":
        _parse_appendix_1(all_pages_text, result)
    else:
        result.warnings.append(f"Unrecognized statement (first 200 chars): {first_text[:200]!r}")

    return result


# --------------------------------------------------------------------------- #
# Detection                                                                   #
# --------------------------------------------------------------------------- #

_STMT_HEADER_RE = re.compile(
    r"Statement\s+(\d+)\s*:", re.IGNORECASE
)


def _detect_statement(first_page_text: str) -> str:
    if "Appendix I" in first_page_text and "Revenue Receipts" in first_page_text:
        return "appendix_1"
    m = _STMT_HEADER_RE.search(first_page_text)
    if m:
        return f"stmt_{int(m.group(1))}"
    return "unknown"


# --------------------------------------------------------------------------- #
# Shared utilities                                                            #
# --------------------------------------------------------------------------- #

# Indian-format number, allowing en-dash ("–") and hyphen-minus ("-") for missing,
# parens for negatives, and lakh-grouped (1,73,767.0) or normal (173,767.0) commas.
_NUM_RE = re.compile(r"-?\(?[\d,]+(?:\.\d+)?\)?")


def _to_decimal(text: str) -> Decimal | None:
    """Parse Indian-format number text to Decimal. Returns None for missing/dash."""
    if text is None:
        return None
    raw = text.strip().replace(",", "").replace("–", "").replace("—", "")
    if raw in ("", "-", "–"):
        return None
    neg = raw.startswith("(") and raw.endswith(")")
    if neg:
        raw = raw[1:-1]
    try:
        val = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    return -val if neg else val


def _ap_line(text: str, prefix: str = "1. Andhra Pradesh") -> str | None:
    """Return the line starting with the AP prefix from a multi-line text block."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped
    return None


def _numbers_from_line(line: str, expected: int | None = None) -> list[Decimal | None]:
    """Extract Indian-formatted numbers from a line, in order. None for '–'/'-'."""
    # Replace en-dash/em-dash placeholders with sentinel to retain position.
    tokens = re.split(r"\s+", line.strip())
    out: list[Decimal | None] = []
    for tok in tokens:
        if tok in ("–", "—", "-"):
            out.append(None)
        elif _NUM_RE.fullmatch(tok):
            out.append(_to_decimal(tok))
    if expected is not None and len(out) != expected:
        # Fall back to broader number scan when token-split misses a value.
        scanned = []
        for m in _NUM_RE.finditer(line):
            scanned.append(_to_decimal(m.group(0)))
        if len(scanned) == expected:
            return scanned
    return out


def _fy_period(fy_label: str) -> tuple[date, date]:
    """Return (period_start, period_end) for a fiscal year label like '2023-24'."""
    start_year = int(fy_label.split("-")[0])
    return date(start_year, 4, 1), date(start_year + 1, 3, 31)


# --------------------------------------------------------------------------- #
# Statement 2: Revenue Receipts / Expenditure / Surplus-Deficit               #
# --------------------------------------------------------------------------- #

def _parse_stmt_2(text: str, result: StateFinancesResult) -> None:
    line = _ap_line(text)
    if line is None:
        result.warnings.append("stmt_2: AP row not found")
        return
    nums = _numbers_from_line(line, expected=9)
    if len(nums) != 9 or any(n is None for n in nums):
        result.warnings.append(f"stmt_2: expected 9 numbers, got {len(nums)} from {line!r}")
        return
    rr_a, re_a, rsd_a, rr_re, re_re, rsd_re, rr_be, re_be, rsd_be = nums
    triples = [
        ("audited_actual", "2023-24", rr_a, re_a, rsd_a),
        ("revised_estimate", "2024-25", rr_re, re_re, rsd_re),
        ("budget_estimate", "2025-26", rr_be, re_be, rsd_be),
    ]
    for basis, fy, rr, re_v, rsd in triples:
        ps, pe = _fy_period(fy)
        prov = _Provenance(page_number=1, row_label="Andhra Pradesh", quoted_text=line)
        result.fiscal_metrics.append(ParsedFiscalMetricRecord(
            metric_code="revenue_receipts_total",
            metric_name="Revenue Receipts (Total)",
            metric_group="receipts",
            basis_tag=basis,
            fiscal_year=fy,
            period_start=ps,
            period_end=pe,
            value_inr_crore=rr,
            department_code="AP",
            provenance=prov,
        ))
        result.fiscal_metrics.append(ParsedFiscalMetricRecord(
            metric_code="revenue_expenditure_total",
            metric_name="Revenue Expenditure (Total)",
            metric_group="expenditure",
            basis_tag=basis,
            fiscal_year=fy,
            period_start=ps,
            period_end=pe,
            value_inr_crore=re_v,
            department_code="AP",
            provenance=prov,
        ))
        # RBI sign convention: positive = revenue deficit, negative = revenue surplus.
        result.fiscal_metrics.append(ParsedFiscalMetricRecord(
            metric_code="revenue_deficit_surplus",
            metric_name="Revenue Deficit(+)/Surplus(-)",
            metric_group="deficit",
            basis_tag=basis,
            fiscal_year=fy,
            period_start=ps,
            period_end=pe,
            value_inr_crore=rsd,
            department_code="AP",
            provenance=prov,
        ))


# --------------------------------------------------------------------------- #
# Statement 13: Interest Payments (Gross / Net*)                              #
# --------------------------------------------------------------------------- #

def _parse_stmt_13(text: str, result: StateFinancesResult) -> None:
    _parse_gross_net_three_year(
        text,
        result,
        metric_gross_code="interest_payments_gross",
        metric_net_code="interest_payments_net",
        metric_name_gross="Interest Payments (Gross)",
        metric_name_net="Interest Payments (Net)",
        metric_group="expenditure",
    )


# --------------------------------------------------------------------------- #
# Statement 16: Loans from the Centre (Gross / Net*)                          #
# --------------------------------------------------------------------------- #

def _parse_stmt_16(text: str, result: StateFinancesResult) -> None:
    _parse_gross_net_three_year(
        text,
        result,
        metric_gross_code="loans_from_centre_gross",
        metric_net_code="loans_from_centre_net",
        metric_name_gross="Loans from the Centre (Gross)",
        metric_name_net="Loans from the Centre (Net)",
        metric_group="receipts",
    )


def _parse_gross_net_three_year(
    text: str,
    result: StateFinancesResult,
    *,
    metric_gross_code: str,
    metric_net_code: str,
    metric_name_gross: str,
    metric_name_net: str,
    metric_group: str,
) -> None:
    line = _ap_line(text)
    if line is None:
        result.warnings.append(f"{metric_gross_code}: AP row not found")
        return
    nums = _numbers_from_line(line)
    # Expected 10 numbers: gross/net for 3 FYs (6) + 4 variation columns.
    if len(nums) < 6:
        result.warnings.append(
            f"{metric_gross_code}: too few numbers ({len(nums)}) on AP line {line!r}"
        )
        return
    gross_a, net_a, gross_re, net_re, gross_be, net_be = nums[:6]
    triples = [
        ("audited_actual", "2023-24", gross_a, net_a),
        ("revised_estimate", "2024-25", gross_re, net_re),
        ("budget_estimate", "2025-26", gross_be, net_be),
    ]
    for basis, fy, g, n in triples:
        if g is None and n is None:
            continue
        ps, pe = _fy_period(fy)
        prov = _Provenance(page_number=1, row_label="Andhra Pradesh", quoted_text=line)
        if g is not None:
            result.fiscal_metrics.append(ParsedFiscalMetricRecord(
                metric_code=metric_gross_code,
                metric_name=metric_name_gross,
                metric_group=metric_group,
                basis_tag=basis,
                fiscal_year=fy,
                period_start=ps,
                period_end=pe,
                value_inr_crore=g,
                department_code="AP",
                provenance=prov,
            ))
        if n is not None:
            result.fiscal_metrics.append(ParsedFiscalMetricRecord(
                metric_code=metric_net_code,
                metric_name=metric_name_net,
                metric_group=metric_group,
                basis_tag=basis,
                fiscal_year=fy,
                period_start=ps,
                period_end=pe,
                value_inr_crore=n,
                department_code="AP",
                provenance=prov,
            ))


# --------------------------------------------------------------------------- #
# Statement 19: Total Outstanding Liabilities (annual time series 2008..2026) #
# --------------------------------------------------------------------------- #

def _parse_stmt_19(text: str, result: StateFinancesResult) -> None:
    line = _ap_line(text)
    if line is None:
        result.warnings.append("stmt_19: AP row not found")
        return
    nums = _numbers_from_line(line)
    if len(nums) != 19:
        result.warnings.append(
            f"stmt_19: expected 19 annual values, got {len(nums)} from {line!r}"
        )
        return
    # Years 2008..2024 = audited, 2025 = RE, 2026 = BE. Period is end-March of that year.
    years = list(range(2008, 2027))  # 19 entries: 2008..2026
    for year, val in zip(years, nums):
        if val is None:
            continue
        if year <= 2024:
            basis = "audited_actual"
            fy_label = f"{year-1}-{str(year)[-2:]}"  # e.g. 2024 -> "2023-24"
        elif year == 2025:
            basis = "revised_estimate"
            fy_label = "2024-25"
        else:
            basis = "budget_estimate"
            fy_label = "2025-26"
        period_start, period_end = _fy_period(fy_label)
        prov = _Provenance(page_number=1, row_label="Andhra Pradesh", quoted_text=line)
        result.fiscal_metrics.append(ParsedFiscalMetricRecord(
            metric_code="total_outstanding_liabilities",
            metric_name="Total Outstanding Liabilities (end-March)",
            metric_group="debt",
            basis_tag=basis,
            fiscal_year=fy_label,
            period_start=period_start,
            period_end=period_end,
            value_inr_crore=val,
            department_code="AP",
            notes=f"As at end-March {year}",
            provenance=prov,
        ))


# --------------------------------------------------------------------------- #
# Statement 21: Market Borrowings (Gross Raised / Repayments)                 #
# --------------------------------------------------------------------------- #

def _parse_stmt_21(text: str, result: StateFinancesResult) -> None:
    line = _ap_line(text)
    if line is None:
        result.warnings.append("stmt_21: AP row not found")
        return
    nums = _numbers_from_line(line, expected=6)
    if len(nums) != 6:
        result.warnings.append(
            f"stmt_21: expected 6 numbers, got {len(nums)} from {line!r}"
        )
        return
    g_a, r_a, g_re, r_re, g_be, r_be = nums
    # Note: 2025-26* is partial (Apr 1 — Dec 16, 2025 per RBI footnote). We tag basis as 'actual'.
    triples = [
        ("audited_actual", "2023-24", g_a, r_a, None),
        ("revised_estimate", "2024-25", g_re, r_re, None),
        ("actual", "2025-26", g_be, r_be, "Partial: Apr 01 - Dec 16, 2025"),
    ]
    for basis, fy, g, r, note in triples:
        ps, pe = _fy_period(fy)
        prov = _Provenance(page_number=1, row_label="Andhra Pradesh", quoted_text=line)
        if g is not None:
            result.fiscal_metrics.append(ParsedFiscalMetricRecord(
                metric_code="market_borrowings_gross_raised",
                metric_name="Market Borrowings — Gross Amount Raised",
                metric_group="debt",
                basis_tag=basis,
                fiscal_year=fy,
                period_start=ps,
                period_end=pe,
                value_inr_crore=g,
                department_code="AP",
                notes=note,
                provenance=prov,
            ))
        if r is not None:
            result.fiscal_metrics.append(ParsedFiscalMetricRecord(
                metric_code="market_borrowings_repayments",
                metric_name="Market Borrowings — Repayments",
                metric_group="debt",
                basis_tag=basis,
                fiscal_year=fy,
                period_start=ps,
                period_end=pe,
                value_inr_crore=r,
                department_code="AP",
                notes=note,
                provenance=prov,
            ))


# --------------------------------------------------------------------------- #
# Statement 22: per-instrument outstanding state government market loans      #
# --------------------------------------------------------------------------- #

# Three instrument-name shapes seen in the AP block of Statement 22:
#   loans_bearing_interest      : "ANDHRA[ PRADESH| PRA]?  SDL|SGS  YYYY[ MON]"
#   special_securities          : "ANDHRA[ PR]?  UDAY BOND|SPL BONDS  YYYY"
#   loans_not_bearing_interest  : "A.P. (S.D|SDL)  YYYY"
# Each "<sr> <coupon>% <NAME> <amount>" tuple. Used with re.finditer so we
# can extract entries from any position in a line (banners, totals, etc.).
_STMT22_ENTRY_RE = re.compile(
    r"(?P<sr>\d{1,4})\s+"
    r"(?P<coupon>\d+(?:\.\d+)?)%\s+"
    r"(?P<name>"
    r"(?:ANDHRA(?:\s+PRADESH|\s+PRA)?\s+(?:SDL|SGS)|"
    r"ANDHRA(?:\s+PR)?\s+(?:UDAY\s+BOND|SPL\s+BONDS)|"
    r"A\.\s*P\.\s+(?:SDL|S\.D))\s+(?P<year>\d{4})"
    r"(?:\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))?"
    r")\s+"
    r"(?P<amount>[\d,]+\.\d{2})",
    re.IGNORECASE,
)


def _stmt22_section_for(name: str) -> str:
    """Map an instrument name to its AP subsection (LBI / SS / LNBI)."""
    upper = name.upper()
    if "UDAY BOND" in upper or "SPL BONDS" in upper:
        return "special_securities"
    if upper.startswith("A.P.") or upper.startswith("A. P."):
        return "loans_not_bearing_interest"
    return "loans_bearing_interest"


# Other states' banners — once we hit one, we leave the AP block. Statement 22
# appears to interleave them with AP entries on shared visual lines, so we
# match anywhere-on-line, but only as a hint to stop ingesting AP entries.
_OTHER_STATE_BANNER_RE = re.compile(
    r"\b(?:ARUNACHAL\s+PRADESH|ASSAM|BIHAR|CHHATTISGARH|GOA|GUJARAT|HARYANA|"
    r"HIMACHAL\s+PRADESH|JAMMU\s+AND\s+KASHMIR|JHARKHAND|KARNATAKA|KERALA|"
    r"MADHYA\s+PRADESH|MAHARASHTRA|MANIPUR|MEGHALAYA|MIZORAM|NAGALAND|"
    r"ODISHA|PUDUCHERRY|PUNJAB|RAJASTHAN|SIKKIM|TAMIL\s+NADU|TELANGANA|"
    r"TRIPURA|UTTAR\s+PRADESH|UTTARAKHAND|WEST\s+BENGAL|NCT\s+DELHI)\b",
    re.IGNORECASE,
)


def _parse_stmt_22(pages_text: list[str], result: StateFinancesResult) -> None:
    """Statement 22 — every AP market loan with balance as of end-March 2025.

    The PDF prints two columns side-by-side per page; pdfplumber linearises
    them, so each text line contains 0, 1 or 2 instrument entries plus any
    banner / subtotal text that sits inline with the table rows. We use
    re.finditer to harvest every entry from each line regardless of position.

    AP has multiple subsections (Loans Bearing Interest, Special Securities,
    Loans not bearing interest) where Sr-numbers restart from 1, so the
    dedupe key is (section, sr).
    """
    as_of_date = date(2025, 3, 31)
    # The regex itself filters to AP-only by requiring ANDHRA / A.P. in the name,
    # so we don't gate on an in-section flag. Other states' SDLs (ARUNACHAL PR
    # SDL, ASSAM SDL, ...) won't match.
    seen: set[tuple[str, int]] = set()

    for page_idx, text in enumerate(pages_text):
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue

            for m in _STMT22_ENTRY_RE.finditer(line):
                sr = int(m["sr"])
                amount = _to_decimal(m["amount"])
                if amount is None:
                    continue
                name = re.sub(r"\s+", " ", m["name"]).strip()
                section = _stmt22_section_for(name)
                key = (section, sr)
                if key in seen:
                    continue
                seen.add(key)
                coupon = _to_decimal(m["coupon"])
                maturity_year = int(m["year"])
                code = _stmt22_code(section, sr, name)
                prov = _Provenance(
                    page_number=page_idx + 1,
                    row_number=sr,
                    row_label=f"[{section}] {name}",
                    quoted_text=line[:200],
                )
                result.debt_positions.append(ParsedDebtPositionRecord(
                    instrument_code=code,
                    instrument_name=name,
                    issuer_name="Government of Andhra Pradesh",
                    as_of_date=as_of_date,
                    basis_tag="actual",
                    outstanding_principal_inr_crore=amount,
                    coupon_rate=coupon,
                    maturity_date=date(maturity_year, 3, 31),
                    provenance=prov,
                ))


def _stmt22_code(section: str, sr: int, name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:50]
    sec_short = {
        "loans_bearing_interest": "lbi",
        "special_securities": "ss",
        "loans_not_bearing_interest": "lnbi",
    }.get(section, section[:6])
    return f"rbi_stmt22_{sec_short}_{sr:04d}_{slug}"


# --------------------------------------------------------------------------- #
# Statement 23: Maturity Profile of Outstanding State Government Securities   #
# --------------------------------------------------------------------------- #

# The bucket headers in the table; the first 16 are individual FY buckets,
# the 17th is the long-tail bucket "2040-2064", followed by TOTAL.
_STMT23_BUCKETS = [
    "2025-2026", "2026-2027", "2027-2028", "2028-2029", "2029-2030",
    "2030-2031", "2031-2032", "2032-2033", "2033-2034", "2034-2035",
    "2035-2036", "2036-2037", "2037-2038", "2038-2039", "2039-2040",
    "2040-2064",
]


def _parse_stmt_23(text: str, result: StateFinancesResult) -> None:
    line = _ap_line(text)
    if line is None:
        result.warnings.append("stmt_23: AP row not found")
        return
    # 16 buckets + 1 TOTAL = 17 numeric values expected.
    nums = _numbers_from_line(line, expected=17)
    if len(nums) != 17:
        result.warnings.append(
            f"stmt_23: expected 17 numbers, got {len(nums)} from {line!r}"
        )
        return
    as_of = date(2025, 3, 31)
    *bucket_vals, total = nums
    for bucket_label, val in zip(_STMT23_BUCKETS, bucket_vals):
        if val is None:
            continue
        # Use first year of the bucket as period_start, last year-end as period_end.
        start_year, end_year = (int(p) for p in bucket_label.split("-"))
        ps = date(start_year, 4, 1)
        pe = date(end_year, 3, 31)
        prov = _Provenance(page_number=1, row_label="Andhra Pradesh", quoted_text=line)
        result.fiscal_metrics.append(ParsedFiscalMetricRecord(
            metric_code=f"maturity_profile_{bucket_label}",
            metric_name=f"Maturity profile (bucket {bucket_label})",
            metric_group="debt",
            basis_tag="actual",
            fiscal_year=f"{start_year}-{str(end_year)[-2:]}",
            period_start=ps,
            period_end=pe,
            value_inr_crore=val,
            department_code="AP",
            notes=f"Outstanding as of {as_of.isoformat()}",
            provenance=prov,
        ))
    if total is not None:
        prov = _Provenance(page_number=1, row_label="Andhra Pradesh — Total", quoted_text=line)
        result.fiscal_metrics.append(ParsedFiscalMetricRecord(
            metric_code="maturity_profile_total",
            metric_name="Maturity profile total (all buckets)",
            metric_group="debt",
            basis_tag="actual",
            fiscal_year="2024-25",
            period_start=date(2024, 4, 1),
            period_end=as_of,
            value_inr_crore=total,
            department_code="AP",
            notes=f"Outstanding as of {as_of.isoformat()}",
            provenance=prov,
        ))


# --------------------------------------------------------------------------- #
# Appendix I: per-item Revenue Receipts breakdown                             #
# --------------------------------------------------------------------------- #

# Source unit is ₹ Lakh; we convert to ₹ Crore for consistency (1 crore = 100 lakh).
# The AP block appears on pages where "ANDHRA PRADESH" is the LEFT column.
# Each AP-only line then has 4 numeric values: 2023-24 Accounts, 2024-25 BE,
# 2024-25 RE, 2025-26 BE. The right column is whichever state appears next
# (Arunachal Pradesh) and we discard those values.
_APPX1_FY_BASES = [
    ("2023-24", "audited_actual"),
    ("2024-25", "budget_estimate"),
    ("2024-25", "revised_estimate"),
    ("2025-26", "budget_estimate"),
]

# Item lines start with characters like '1.' / '2.' / 'TOTAL ' / 'I. ' / 'A. '
# / '(i)' etc. We extract the leading label up to the first run of numbers.
_APPX1_NUM_TOKEN = re.compile(r"-?[\d,]+\.\d+")


def _parse_appendix_1(pages_text: list[str], result: StateFinancesResult) -> None:
    """Extract AP-block per-item revenue receipts.

    Pages 1-2 carry the AP+Arunachal block. We parse only the first 4 numeric
    columns per line (AP). Item labels can wrap across multiple lines; we
    accumulate non-numeric prefix text and emit a record once we see numbers.
    """
    seen_codes: set[str] = set()
    for page_idx in range(min(2, len(pages_text))):  # AP is in pages 1 + 2
        text = pages_text[page_idx]
        if "ANDHRA PRADESH" not in text.upper():
            continue
        accumulated_label: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(("Appendix I", "Item", "ANDHRA PRADESH",
                                 "ARUNACHAL PRADESH", "(₹", "1 2 3 4 5",
                                 "(Accounts)", "(Budget", "(Revised",
                                 "Estimates)", "State Finances")):
                accumulated_label.clear()
                continue
            nums = _APPX1_NUM_TOKEN.findall(line)
            if len(nums) >= 4:
                # Take label = text before the first number.
                first_num_pos = line.find(nums[0])
                label_part = line[:first_num_pos].strip(" .:")
                full_label = " ".join([*accumulated_label, label_part]).strip()
                accumulated_label.clear()
                if not full_label:
                    continue
                code = _appx1_code(full_label)
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                ap_vals = [_to_decimal(n) for n in nums[:4]]
                prov_quote = line[:200]
                for (fy, basis), val_lakh in zip(_APPX1_FY_BASES, ap_vals):
                    if val_lakh is None:
                        continue
                    val_crore = val_lakh / Decimal(100)
                    ps, pe = _fy_period(fy)
                    result.fiscal_metrics.append(ParsedFiscalMetricRecord(
                        metric_code=f"appx1_{code}",
                        metric_name=full_label,
                        metric_group="receipts",
                        basis_tag=basis,
                        fiscal_year=fy,
                        period_start=ps,
                        period_end=pe,
                        value_inr_crore=val_crore,
                        department_code="AP",
                        notes="Source: RBI State Finances Appendix I (₹ Lakh in source, converted to ₹ Crore)",
                        provenance=_Provenance(
                            page_number=page_idx + 1,
                            row_label=full_label,
                            quoted_text=prov_quote,
                        ),
                    ))
            else:
                # Continuation line — accumulate label.
                if line and not _APPX1_NUM_TOKEN.search(line):
                    accumulated_label.append(line)


def _appx1_code(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")
    return slug[:80]
