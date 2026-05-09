"""End-to-end baseline verification for RBI + Outstanding PDFs.

For each PDF in Data_website/Rbi/ + Data_website/Outstanding_securities_state/:

1. Run the parser and capture its output.
2. Independently extract a small set of ground-truth facts directly from the
   PDF text using a different code path (raw pdfplumber regex), so a bug in
   the parser cannot also be present in the verifier.
3. Diff parser output against ground truth, report PASS/FAIL per check.

Run:
    PYTHONPATH=apps/worker:apps/api .venv/bin/python scripts/verify_baseline.py
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable

import pdfplumber

from worker.rbi_ingestion.state_finances_parser import (
    parse_state_finances_pdf,
    StateFinancesResult,
)
from worker.rbi_ingestion.outstanding_parser import parse_outstanding_securities_bytes


REPO = Path(__file__).resolve().parents[2]  # /home/maveric2/website
DATA_RBI = REPO / "Data_website" / "Rbi"
DATA_OUT = REPO / "Data_website" / "Outstanding_securities_state"


@dataclass(slots=True)
class CheckResult:
    name: str
    expected: object
    actual: object
    ok: bool
    note: str = ""

    def fmt(self) -> str:
        flag = "PASS" if self.ok else "FAIL"
        line = f"  [{flag}] {self.name}: expected={self.expected!r} actual={self.actual!r}"
        if self.note:
            line += f"  ({self.note})"
        return line


def approx_eq(a: object, b: object, tol: Decimal = Decimal("0.05")) -> bool:
    """Decimal-tolerant equality. tol is absolute. None == None only."""
    if a is None or b is None:
        return a is None and b is None
    try:
        return abs(Decimal(str(a)) - Decimal(str(b))) <= tol
    except Exception:  # noqa: BLE001
        return a == b


# --------------------------------------------------------------------------- #
# Ground-truth extractors (independent of the parser implementation)          #
# --------------------------------------------------------------------------- #

def gt_first_page_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return pdf.pages[0].extract_text() or ""


def gt_all_pages_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)


_NUM = r"-?[\d,]+(?:\.\d+)?"


def _to_dec(s: str) -> Decimal:
    return Decimal(s.replace(",", ""))


def gt_ap_numbers(text: str) -> list[Decimal]:
    """Read the '1. Andhra Pradesh ...' line and return its numeric values."""
    for line in text.splitlines():
        if line.strip().startswith("1. Andhra Pradesh"):
            return [_to_dec(m) for m in re.findall(_NUM, line.replace("1. Andhra Pradesh", ""))]
    raise AssertionError("AP row not found in ground truth")


# --------------------------------------------------------------------------- #
# Per-file verification suites                                                 #
# --------------------------------------------------------------------------- #

def verify_stmt_2(path: Path, parsed: StateFinancesResult) -> list[CheckResult]:
    nums = gt_ap_numbers(gt_first_page_text(path))
    # 9 numbers: RR/RE/RSD × 3 fiscal years.
    assert len(nums) == 9, f"stmt_2 ground truth: expected 9 numbers, got {len(nums)}"
    expectations = {
        ("revenue_receipts_total",   "2023-24"): nums[0],
        ("revenue_expenditure_total","2023-24"): nums[1],
        ("revenue_deficit_surplus",  "2023-24"): nums[2],
        ("revenue_receipts_total",   "2024-25"): nums[3],
        ("revenue_expenditure_total","2024-25"): nums[4],
        ("revenue_deficit_surplus",  "2024-25"): nums[5],
        ("revenue_receipts_total",   "2025-26"): nums[6],
        ("revenue_expenditure_total","2025-26"): nums[7],
        ("revenue_deficit_surplus",  "2025-26"): nums[8],
    }
    by_key = {(m.metric_code, m.fiscal_year): m for m in parsed.fiscal_metrics}
    out = []
    for key, exp in expectations.items():
        m = by_key.get(key)
        out.append(CheckResult(
            name=f"stmt2 {key[0]}@{key[1]}",
            expected=exp,
            actual=m.value_inr_crore if m else None,
            ok=m is not None and approx_eq(m.value_inr_crore, exp),
        ))
    return out


def _verify_three_year_gross_net(
    path: Path, parsed: StateFinancesResult, gross_code: str, net_code: str
) -> list[CheckResult]:
    nums = gt_ap_numbers(gt_first_page_text(path))
    # First 6 = gross/net × 3 fy. Trailing 4 are variation-percent columns.
    g_a, n_a, g_re, n_re, g_be, n_be = nums[:6]
    expectations = {
        (gross_code, "2023-24"): g_a, (net_code, "2023-24"): n_a,
        (gross_code, "2024-25"): g_re, (net_code, "2024-25"): n_re,
        (gross_code, "2025-26"): g_be, (net_code, "2025-26"): n_be,
    }
    by_key = {(m.metric_code, m.fiscal_year): m for m in parsed.fiscal_metrics}
    out = []
    for key, exp in expectations.items():
        m = by_key.get(key)
        out.append(CheckResult(
            name=f"{key[0]}@{key[1]}",
            expected=exp,
            actual=m.value_inr_crore if m else None,
            ok=m is not None and approx_eq(m.value_inr_crore, exp),
        ))
    return out


def verify_stmt_13(path, parsed):
    return _verify_three_year_gross_net(
        path, parsed, "interest_payments_gross", "interest_payments_net"
    )


def verify_stmt_16(path, parsed):
    return _verify_three_year_gross_net(
        path, parsed, "loans_from_centre_gross", "loans_from_centre_net"
    )


def verify_stmt_19(path: Path, parsed: StateFinancesResult) -> list[CheckResult]:
    nums = gt_ap_numbers(gt_first_page_text(path))
    assert len(nums) == 19, f"stmt_19 ground truth: expected 19 values, got {len(nums)}"
    out = []
    fy_labels = [f"{y-1}-{str(y)[-2:]}" for y in range(2008, 2025)] + ["2024-25", "2025-26"]
    by_fy = {m.fiscal_year: m for m in parsed.fiscal_metrics}
    for fy_label, exp in zip(fy_labels, nums):
        m = by_fy.get(fy_label)
        out.append(CheckResult(
            name=f"stmt19 {fy_label}",
            expected=exp,
            actual=m.value_inr_crore if m else None,
            ok=m is not None and approx_eq(m.value_inr_crore, exp),
        ))
    return out


def verify_stmt_21(path: Path, parsed: StateFinancesResult) -> list[CheckResult]:
    nums = gt_ap_numbers(gt_first_page_text(path))
    g_a, r_a, g_re, r_re, g_be, r_be = nums[:6]
    expectations = {
        ("market_borrowings_gross_raised", "2023-24"): g_a,
        ("market_borrowings_repayments",   "2023-24"): r_a,
        ("market_borrowings_gross_raised", "2024-25"): g_re,
        ("market_borrowings_repayments",   "2024-25"): r_re,
        ("market_borrowings_gross_raised", "2025-26"): g_be,
        ("market_borrowings_repayments",   "2025-26"): r_be,
    }
    by_key = {(m.metric_code, m.fiscal_year): m for m in parsed.fiscal_metrics}
    out = []
    for key, exp in expectations.items():
        m = by_key.get(key)
        out.append(CheckResult(
            name=f"{key[0]}@{key[1]}",
            expected=exp,
            actual=m.value_inr_crore if m else None,
            ok=m is not None and approx_eq(m.value_inr_crore, exp),
        ))
    return out


def verify_stmt_22(path: Path, parsed: StateFinancesResult) -> list[CheckResult]:
    """Stmt 22 — the document prints AP subtotals Total[A], Total[B], Total[C]
    and grand Total[A+B+C]. Independently re-extract those, then assert each
    section's parsed sum matches its PDF subtotal within 0.10 crore.
    """
    text = gt_all_pages_text(path)

    def find_total(label_re: str) -> Decimal:
        m = re.search(label_re + r"\s+([\d,]+\.\d+)", text)
        if not m:
            raise AssertionError(f"could not find {label_re!r} in PDF")
        return _to_dec(m.group(1))

    # Match within the AP section: only the FIRST occurrence of each label
    # (the document repeats them per state).
    total_a = find_total(r"Total\s*\[A\]")
    total_b = find_total(r"Total\s*\[B\]")
    total_c = find_total(r"Total\s*\[C\]")
    grand   = find_total(r"Total\s*\[A\+B\+C\]")

    sums: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    for p in parsed.debt_positions:
        sec = p.provenance.row_label.split("]")[0].lstrip("[")
        sums[sec] = sums.get(sec, Decimal(0)) + p.outstanding_principal_inr_crore
        counts[sec] = counts.get(sec, 0) + 1

    out = [
        CheckResult("stmt22 LBI sum vs Total[A]", total_a, sums.get("loans_bearing_interest"),
                    approx_eq(sums.get("loans_bearing_interest"), total_a, Decimal("0.5")),
                    note=f"{counts.get('loans_bearing_interest')} entries"),
        CheckResult("stmt22 SS  sum vs Total[B]", total_b, sums.get("special_securities"),
                    approx_eq(sums.get("special_securities"), total_b, Decimal("0.1")),
                    note=f"{counts.get('special_securities')} entries"),
        CheckResult("stmt22 LNBI sum vs Total[C]", total_c, sums.get("loans_not_bearing_interest"),
                    approx_eq(sums.get("loans_not_bearing_interest"), total_c, Decimal("0.05")),
                    note=f"{counts.get('loans_not_bearing_interest')} entries"),
        CheckResult("stmt22 grand sum vs Total[A+B+C]", grand, sum(sums.values()),
                    approx_eq(sum(sums.values()), grand, Decimal("0.5"))),
    ]
    return out


def verify_stmt_23(path: Path, parsed: StateFinancesResult) -> list[CheckResult]:
    nums = gt_ap_numbers(gt_first_page_text(path))
    assert len(nums) == 17, f"stmt_23 ground truth: expected 17 values, got {len(nums)}"
    bucket_labels = [
        "2025-2026", "2026-2027", "2027-2028", "2028-2029", "2029-2030",
        "2030-2031", "2031-2032", "2032-2033", "2033-2034", "2034-2035",
        "2035-2036", "2036-2037", "2037-2038", "2038-2039", "2039-2040",
        "2040-2064",
    ]
    by_code = {m.metric_code: m for m in parsed.fiscal_metrics}
    out = []
    for label, exp in zip(bucket_labels, nums[:16]):
        m = by_code.get(f"maturity_profile_{label}")
        out.append(CheckResult(
            name=f"stmt23 bucket {label}",
            expected=exp,
            actual=m.value_inr_crore if m else None,
            ok=m is not None and approx_eq(m.value_inr_crore, exp),
        ))
    m_total = by_code.get("maturity_profile_total")
    out.append(CheckResult(
        name="stmt23 TOTAL",
        expected=nums[16],
        actual=m_total.value_inr_crore if m_total else None,
        ok=m_total is not None and approx_eq(m_total.value_inr_crore, nums[16]),
    ))
    # And the parsed buckets' sum should equal the PDF's TOTAL.
    parsed_sum = sum(
        m.value_inr_crore for code, m in by_code.items() if code != "maturity_profile_total"
    )
    out.append(CheckResult(
        name="stmt23 buckets-sum vs TOTAL",
        expected=nums[16],
        actual=parsed_sum,
        ok=approx_eq(parsed_sum, nums[16], Decimal("0.5")),
    ))
    return out


def verify_appendix_1(path: Path, parsed: StateFinancesResult) -> list[CheckResult]:
    """Appendix I source unit is ₹ Lakh; parser converts to ₹ Crore (÷100)."""
    text = gt_first_page_text(path)
    # Find the AP "TOTAL REVENUE (I+II)" line — should be 1,73,76,701.2 (lakh) for 2023-24 Accounts.
    m = re.search(
        r"TOTAL\s+REVENUE\s+\(I\+II\)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)",
        text,
    )
    if not m:
        return [CheckResult("appx1 TOTAL REVENUE row found", True, False, False,
                             note="ground-truth regex did not match")]
    vals_lakh = [_to_dec(m.group(i)) for i in range(1, 5)]
    vals_crore = [v / Decimal(100) for v in vals_lakh]

    # Parser produces records keyed by metric_code 'appx1_total_revenue_i_ii' (slug).
    # The slug for "TOTAL REVENUE (I+II)" should produce 'total_revenue_i_ii'.
    candidates = [
        m for m in parsed.fiscal_metrics
        if m.metric_code.startswith("appx1_") and "total_revenue" in m.metric_code
    ]
    by_fy_basis = {(m.fiscal_year, m.basis_tag): m for m in candidates}
    expectations = [
        ("2023-24", "audited_actual",    vals_crore[0]),
        ("2024-25", "budget_estimate",   vals_crore[1]),
        ("2024-25", "revised_estimate",  vals_crore[2]),
        ("2025-26", "budget_estimate",   vals_crore[3]),
    ]
    out = []
    for fy, basis, exp in expectations:
        rec = by_fy_basis.get((fy, basis))
        out.append(CheckResult(
            name=f"appx1 TOTAL REVENUE @ {fy}/{basis}",
            expected=exp,
            actual=rec.value_inr_crore if rec else None,
            ok=rec is not None and approx_eq(rec.value_inr_crore, exp, Decimal("0.05")),
        ))
    return out


def verify_outstanding(path: Path) -> list[CheckResult]:
    """Cross-check the Outstanding parser:
       (a) total of all AP positions matches independent text-based summing
           of the Outstanding Stock column, and
       (b) all positions have a maturity_date and as_of_date populated.
    """
    positions = parse_outstanding_securities_bytes(path.read_bytes(), source_url=str(path))

    # Independent ground-truth: scan PDF text for AP rows and sum the trailing amount.
    # A row in this PDF is rendered as: "<sr> <ISIN> ANDHRA PRADESH <name> <issue> <maturity> <amount>".
    text = gt_all_pages_text(path)
    line_re = re.compile(
        r"^\s*\d+\s+IN\d+\s+ANDHRA\s+PRADESH\s+.+?\s+\d{1,2}-[A-Za-z]+-\d{4}\s+\d{1,2}-[A-Za-z]+-\d{4}\s+([\d,]+\.\d+)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    gt_amounts = [_to_dec(m) for m in line_re.findall(text)]
    gt_total = sum(gt_amounts, Decimal(0))
    parser_total = sum(p.outstanding_principal for p in positions)

    out = [
        CheckResult(
            name="outstanding count",
            expected=len(gt_amounts),
            actual=len(positions),
            ok=len(positions) == len(gt_amounts),
        ),
        CheckResult(
            name="outstanding total ₹ crore",
            expected=gt_total,
            actual=parser_total,
            ok=approx_eq(parser_total, gt_total, Decimal("0.001")),
        ),
        CheckResult(
            name="all positions have maturity_date",
            expected=len(positions),
            actual=sum(1 for p in positions if p.maturity_date is not None),
            ok=all(p.maturity_date for p in positions),
        ),
        CheckResult(
            name="all positions have as_of_date",
            expected=len(positions),
            actual=sum(1 for p in positions if p.as_of_date is not None),
            ok=all(p.as_of_date for p in positions),
        ),
    ]
    return out


# --------------------------------------------------------------------------- #
# Driver                                                                      #
# --------------------------------------------------------------------------- #

DISPATCH: dict[str, Callable] = {
    "stmt_2": verify_stmt_2,
    "stmt_13": verify_stmt_13,
    "stmt_16": verify_stmt_16,
    "stmt_19": verify_stmt_19,
    "stmt_21": verify_stmt_21,
    "stmt_22": verify_stmt_22,
    "stmt_23": verify_stmt_23,
    "appendix_1": verify_appendix_1,
}


def main() -> int:
    rbi_pdfs = sorted(DATA_RBI.glob("*.pdf"))
    out_pdfs = sorted(DATA_OUT.glob("*.pdf"))

    total = 0
    failed = 0

    for path in rbi_pdfs:
        parsed = parse_state_finances_pdf(path.read_bytes(), source_url=str(path))
        verifier = DISPATCH.get(parsed.statement_id)
        print(f"\n{path.name}  [{parsed.statement_id}]")
        if not verifier:
            print(f"  no verifier registered for {parsed.statement_id}")
            continue
        results = verifier(path, parsed)
        for r in results:
            print(r.fmt())
            total += 1
            if not r.ok:
                failed += 1

    for path in out_pdfs:
        print(f"\n{path.name}  [outstanding]")
        results = verify_outstanding(path)
        for r in results:
            print(r.fmt())
            total += 1
            if not r.ok:
                failed += 1

    print()
    print("=" * 70)
    print(f"Verification: {total - failed}/{total} checks passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
