from __future__ import annotations

from urllib.parse import unquote, urlsplit


RBI_SOURCE_FAMILIES = {
    "sdl_calendar",
    "sdl_auction_notification",
    "sdl_auction_result",
    "wma_od",
    "framework",
}


def classify_rbi_source_family(url: str, page_title: str = "", anchor_text: str = "") -> str:
    haystack = " ".join(
        [
            unquote(urlsplit(url).path),
            urlsplit(url).query,
            page_title,
            anchor_text,
        ]
    ).lower()

    if any(token in haystack for token in {"calendar", "indicative", "issuance calendar", "sdl calendar"}):
        return "sdl_calendar"
    if any(token in haystack for token in {"auction notification", "notified amount", "notification"}):
        return "sdl_auction_notification"
    if any(token in haystack for token in {"auction result", "cut-off", "accepted amount", "result"}):
        return "sdl_auction_result"
    if any(token in haystack for token in {"wma", "overdraft", "od", "ways and means"}):
        return "wma_od"
    return "framework"


def infer_event_type(source_family: str, text_hint: str = "") -> str:
    text = text_hint.lower()
    if "issued" in text or "accepted" in text or source_family == "sdl_auction_result":
        return "issued"
    if "notified" in text or source_family == "sdl_auction_notification":
        return "notified"
    return "scheduled"
