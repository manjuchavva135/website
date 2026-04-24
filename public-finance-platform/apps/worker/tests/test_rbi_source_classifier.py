from worker.rbi_ingestion.source_classifier import classify_rbi_source_family, infer_event_type


def test_classify_rbi_source_family() -> None:
    assert classify_rbi_source_family("https://rbi.org.in/sdl/calendar-2026.html") == "sdl_calendar"
    assert classify_rbi_source_family("https://rbi.org.in/docs/auction-notification.pdf") == "sdl_auction_notification"
    assert classify_rbi_source_family("https://rbi.org.in/docs/auction-result.pdf") == "sdl_auction_result"
    assert classify_rbi_source_family("https://rbi.org.in/press/wma-od-release.html") == "wma_od"


def test_infer_event_type() -> None:
    assert infer_event_type("sdl_calendar", text_hint="scheduled auction") == "scheduled"
    assert infer_event_type("sdl_auction_notification", text_hint="notified amount") == "notified"
    assert infer_event_type("sdl_auction_result", text_hint="accepted amount") == "issued"
