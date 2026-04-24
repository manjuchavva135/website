from worker.tasks.ingest import _source_specs


def test_source_specs_contains_seed_urls() -> None:
    specs = _source_specs()
    names = {item["name"] for item in specs}
    urls = {item["url"] for item in specs}
    assert {
        "rbi_faq_711",
        "rbi_faq_3337",
        "rbi_press_releases",
        "ap_budget",
        "ap_frbm",
        "cag_state_accounts_ap",
    } == names
    assert {
        "https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=711",
        "https://www.rbi.org.in/commonman/english/scripts/FAQs.aspx?Id=3337",
        "https://www.rbi.org.in/commonman/english/scripts/PressReleases.aspx",
        "https://apfinance.gov.in/budget.html",
        "https://apfinance.gov.in/frbmreport.html",
        "https://cag.gov.in/en/state-accounts-report?defuat_state_id=64",
    } == urls
