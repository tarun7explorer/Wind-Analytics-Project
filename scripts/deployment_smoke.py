"""Check a deployed Wind Analytics frontend and API using live HTTP requests."""

from __future__ import annotations

import argparse
import json
import sys
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class AssetCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"src", "href"} and value and value.startswith("/assets/"):
                self.paths.add(value)


def get_response(url: str) -> tuple[int, str, bytes]:
    request = Request(url, headers={"Accept": "text/html,application/json", "User-Agent": "wind-analytics-smoke/1.0"})
    try:
        with urlopen(request, timeout=40) as response:
            return response.status, response.headers.get("Content-Type", ""), response.read()
    except HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), exc.read()


def require_json(url: str, required_keys: set[str]) -> dict:
    status, content_type, body = get_response(url)
    print(f"{status} {url} [{content_type}]")
    if not 200 <= status < 300:
        raise RuntimeError(f"HTTP {status} from {url}: {body[:300].decode('utf-8', errors='replace')}")
    if "json" not in content_type.lower():
        raise RuntimeError(f"Expected JSON from {url}, received {content_type!r}")
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Malformed JSON from {url}: {exc}") from exc
    if not isinstance(payload, dict) or not required_keys.issubset(payload):
        missing = required_keys.difference(payload if isinstance(payload, dict) else {})
        raise RuntimeError(f"Unexpected response from {url}; missing keys: {sorted(missing)}")
    return payload


def smoke(base_url: str, year: int, month: int) -> None:
    base_url = base_url.rstrip("/")

    status, content_type, body = get_response(base_url + "/")
    print(f"{status} {base_url}/ [{content_type}]")
    if not 200 <= status < 300 or "html" not in content_type.lower():
        raise RuntimeError(f"Frontend root did not return HTML (HTTP {status})")
    html = body.decode("utf-8", errors="replace")
    if '<div id="root"' not in html and "id='root'" not in html:
        raise RuntimeError("Frontend response does not contain the React root element")
    assets = AssetCollector()
    assets.feed(html)
    if not assets.paths:
        raise RuntimeError("Frontend HTML did not reference any built /assets files")
    for path in sorted(assets.paths):
        asset_status, asset_type, asset_body = get_response(base_url + path)
        print(f"{asset_status} {base_url}{path} [{asset_type}]")
        if not 200 <= asset_status < 300 or not asset_body:
            raise RuntimeError(f"Frontend asset is unavailable: {path} (HTTP {asset_status})")

    require_json(base_url + "/health", {"status"})
    query = urlencode({"year": year, "month": month})
    monthly = require_json(base_url + f"/api/analytics/monthly?{query}", {"year", "month", "hourly_analysis"})
    if monthly["year"] != year or monthly["month"] != month:
        raise RuntimeError("Monthly response period does not match the requested period")
    require_json(base_url + f"/api/analytics/records?{query}&offset=0&limit=2", {"total", "records"})
    report = require_json(base_url + f"/api/analytics/report?{query}", {"records", "hourly_records", "hourly_analysis"})
    if not report["records"] or not report["hourly_records"]:
        raise RuntimeError("Full report returned no source or hourly records")
    print("Deployment smoke checks passed.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url", help="Deployed site origin, e.g. https://example.vercel.app")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=1)
    args = parser.parse_args()
    try:
        smoke(args.base_url, args.year, args.month)
    except (RuntimeError, URLError, TimeoutError) as exc:
        print(f"Deployment smoke check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
