from __future__ import annotations

from posixpath import normpath
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit


TRACKING_QUERY_PARAMS = {
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
    "fbclid",
    "gclid",
}


def canonicalize_url(url: str, base_url: str | None = None) -> str:
    absolute_url = urljoin(base_url, url) if base_url else url
    parts = urlsplit(absolute_url)
    scheme = (parts.scheme or "https").lower()
    netloc = parts.netloc.lower()
    path = parts.path or "/"

    normalized_path = normpath(path)
    if not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    if path.endswith("/") and not normalized_path.endswith("/"):
        normalized_path = f"{normalized_path}/"

    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_PARAMS
    ]
    normalized_query = urlencode(sorted(filtered_query))

    return urlunsplit((scheme, netloc, normalized_path, normalized_query, ""))