from __future__ import annotations

from urllib.parse import unquote, urlsplit


def classify_document_family(
    url: str,
    anchor_text: str = "",
    page_title: str = "",
    family_hint: str | None = None,
) -> str:
    haystack = " ".join(
        [
            family_hint or "",
            anchor_text,
            page_title,
            unquote(urlsplit(url).path),
            urlsplit(url).query,
        ]
    ).lower()

    if any(token in haystack for token in {"frbm", "fiscal responsibility", "budget management"}):
        return "frbm_report"
    if any(token in haystack for token in {"budget", "annual financial statement", "demands for grants"}):
        return "budget"
    if any(token in haystack for token in {"press release", "pressreleases"}):
        return "press_release"
    if any(
        token in haystack
        for token in {"state accounts", "state-accounts", "finance accounts", "appropriation accounts"}
    ):
        return "state_accounts"
    if any(token in haystack for token in {"debt", "loan", "borrowing", "security", "bond"}):
        return "debt"
    if any(token in haystack for token in {"faq", "frequently asked"}):
        return "faq"
    return family_hint or "official_publication"