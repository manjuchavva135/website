from __future__ import annotations

from dataclasses import dataclass
from time import sleep

import httpx

from worker.crawler.detection import detect_anti_bot_signals


@dataclass(frozen=True, slots=True)
class FetchOutcome:
    url: str
    status_code: int
    payload: bytes
    text: str
    content_type: str | None
    anti_bot_signals: list[str]


class APFetchClient:
    def __init__(
        self,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.http_client = http_client or httpx.Client()

    def fetch(self, url: str) -> FetchOutcome:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.http_client.get(
                    url,
                    timeout=self.timeout_seconds,
                    follow_redirects=True,
                    headers={"User-Agent": "public-finance-platform-ap/1.0"},
                )
                response.raise_for_status()
                return FetchOutcome(
                    url=str(response.url),
                    status_code=response.status_code,
                    payload=response.content,
                    text=response.text,
                    content_type=response.headers.get("content-type"),
                    anti_bot_signals=detect_anti_bot_signals(
                        html=response.text,
                        headers=dict(response.headers.items()),
                        status_code=response.status_code,
                    ),
                )
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                sleep(self.backoff_seconds * attempt)
        if last_error is None:
            raise RuntimeError("fetch failed without exception")
        raise last_error
