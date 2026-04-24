from __future__ import annotations

from collections.abc import Mapping


CHALLENGE_MARKERS = {
    "access denied",
    "attention required",
    "bot verification",
    "captcha",
    "cf-browser-verification",
    "cloudflare",
    "datadome",
    "human verification",
    "just a moment",
    "perimeterx",
    "recaptcha",
}


def detect_anti_bot_signals(
    html: str,
    headers: Mapping[str, str] | None = None,
    status_code: int | None = None,
) -> list[str]:
    body = html.lower()
    header_pairs = {str(key).lower(): str(value).lower() for key, value in (headers or {}).items()}
    signals: list[str] = []

    for marker in sorted(CHALLENGE_MARKERS):
        if marker in body:
            signals.append(f"body:{marker}")

    for key, value in header_pairs.items():
        combined = f"{key}:{value}"
        if any(marker in combined for marker in {"akamai", "cf-ray", "cloudflare", "datadome", "perimeterx"}):
            signals.append(f"header:{key}")

    if status_code in {403, 429, 503} and signals:
        signals.append(f"status:{status_code}")

    return signals


def detect_anti_bot_page(
    html: str,
    headers: Mapping[str, str] | None = None,
    status_code: int | None = None,
) -> bool:
    return bool(detect_anti_bot_signals(html=html, headers=headers, status_code=status_code))