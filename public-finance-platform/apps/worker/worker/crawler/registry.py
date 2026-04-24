from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceRegistryEntry:
    source_name: str
    publisher: str
    entrypoint_url: str
    family_hint: str


class SourceRegistry:
    def __init__(self, entries: list[SourceRegistryEntry]) -> None:
        self._entries = entries

    @classmethod
    def default(cls) -> "SourceRegistry":
        return cls(
            entries=[
                SourceRegistryEntry(
                    source_name="rbi_faq_711",
                    publisher="Reserve Bank of India",
                    entrypoint_url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711",
                    family_hint="faq",
                ),
                SourceRegistryEntry(
                    source_name="rbi_faq_3337",
                    publisher="Reserve Bank of India",
                    entrypoint_url="https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3337",
                    family_hint="faq",
                ),
                SourceRegistryEntry(
                    source_name="rbi_press_releases",
                    publisher="Reserve Bank of India",
                    entrypoint_url="https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx",
                    family_hint="press_release",
                ),
                SourceRegistryEntry(
                    source_name="ap_budget",
                    publisher="Andhra Pradesh Finance Department",
                    entrypoint_url="https://apfinance.gov.in/budget.html",
                    family_hint="budget",
                ),
                SourceRegistryEntry(
                    source_name="ap_frbm",
                    publisher="Andhra Pradesh Finance Department",
                    entrypoint_url="https://apfinance.gov.in/frbmreport.html",
                    family_hint="frbm_report",
                ),
                SourceRegistryEntry(
                    source_name="cag_state_accounts_ap",
                    publisher="Comptroller and Auditor General of India",
                    entrypoint_url="https://cag.gov.in/en/state-accounts-report?defuat_state_id=64",
                    family_hint="state_accounts",
                ),
            ]
        )

    def list_entries(self) -> list[SourceRegistryEntry]:
        return list(self._entries)