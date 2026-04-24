import httpx

from worker.rbi_ingestion.fetcher import FetchClient


class FlakyTransport:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.calls < 3:
            raise httpx.ConnectTimeout("timed out", request=request)
        return httpx.Response(200, text="ok", request=request)


class AntiBotTransport:
    def __call__(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="<html>Just a moment... CAPTCHA</html>",
            headers={"cf-ray": "abc"},
            request=request,
        )


def test_fetcher_retries_on_transient_failures() -> None:
    transport = FlakyTransport()
    client = httpx.Client(transport=httpx.MockTransport(transport))
    fetcher = FetchClient(timeout_seconds=1.0, max_retries=3, backoff_seconds=0.0, http_client=client)

    outcome = fetcher.fetch("https://example.org/data")

    assert outcome.status_code == 200
    assert transport.calls == 3


def test_fetcher_flags_anti_bot_signals() -> None:
    client = httpx.Client(transport=httpx.MockTransport(AntiBotTransport()))
    fetcher = FetchClient(timeout_seconds=1.0, max_retries=1, backoff_seconds=0.0, http_client=client)

    outcome = fetcher.fetch("https://example.org/challenge")

    assert outcome.anti_bot_signals
