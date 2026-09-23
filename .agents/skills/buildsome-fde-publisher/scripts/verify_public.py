#!/usr/bin/env python3
"""Verify the public Buildsome FDE gallery and one deployed Demo."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.parse
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--origin", default="https://buildsome.me")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--check-www", action="store_true")
    parser.add_argument("--timeout", type=float, default=20)
    return parser.parse_args()


def fetch(url: str, timeout: float) -> tuple[str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "buildsome-fde-verifier/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"{url} returned HTTP {response.status}")
        content_type = response.headers.get_content_type()
        body = response.read().decode("utf-8", errors="replace")
        print(f"PASS {url} -> {response.geturl()} HTTP {response.status} {content_type}")
        return response.geturl(), body


def main() -> int:
    args = parse_args()
    origin = args.origin.rstrip("/")
    urls = [
        origin + "/",
        origin + "/fde-demo/",
        origin + f"/fde-demo/{args.slug}/",
    ]
    if args.check_www:
        parsed = urllib.parse.urlsplit(origin)
        host = parsed.hostname or ""
        if not host.startswith("www."):
            netloc = "www." + host
            if parsed.port:
                netloc += f":{parsed.port}"
            urls.append(urllib.parse.urlunsplit((parsed.scheme, netloc, "/fde-demo/", "", "")))

    try:
        pages = {url: fetch(url, args.timeout)[1] for url in urls}
        gallery = pages[origin + "/fde-demo/"]
        demo = pages[origin + f"/fde-demo/{args.slug}/"]
        if args.title not in gallery:
            raise RuntimeError("gallery is missing the Demo title")
        if f'/fde-demo/{args.slug}' not in gallery:
            raise RuntimeError("gallery is missing the Demo href")
        title_match = re.search(r"<title>(.*?)</title>", demo, re.IGNORECASE | re.DOTALL)
        if not title_match:
            raise RuntimeError("Demo page has no HTML title")
        asset_urls = set(re.findall(r'(?:src|href)=["\']([^"\']+\.(?:css|js))(?:\?[^"\']*)?["\']', demo))
        for asset in sorted(asset_urls):
            fetch(urllib.parse.urljoin(origin + f"/fde-demo/{args.slug}/", asset), args.timeout)
    except (OSError, RuntimeError, urllib.error.URLError) as error:
        print(f"ERROR {error}", file=sys.stderr)
        return 1

    print("status=healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
