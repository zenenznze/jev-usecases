#!/usr/bin/env python3
"""Validate a Buildsome FDE card and its corresponding Demo source/output."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TEXT_SUFFIXES = {".astro", ".css", ".html", ".js", ".json", ".mjs", ".ts", ".tsx"}
NETWORK_PATTERNS = {
    "fetch": re.compile(r"\bfetch\s*\("),
    "XMLHttpRequest": re.compile(r"\bXMLHttpRequest\b"),
    "WebSocket": re.compile(r"\bWebSocket\s*\("),
    "EventSource": re.compile(r"\bEventSource\s*\("),
    "sendBeacon": re.compile(r"\bsendBeacon\s*\("),
    "external URL": re.compile(r"https?://", re.IGNORECASE),
    "API path": re.compile(r"(?:['\"]|`)\/api\/"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--mode", choices=("replay", "live"), required=True)
    parser.add_argument("--dist", action="store_true", help="also require built output")
    return parser.parse_args()


def text_files(path: Path):
    if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
        yield path
    elif path.is_dir():
        for item in path.rglob("*"):
            if item.is_file() and item.suffix.lower() in TEXT_SUFFIXES:
                yield item


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    errors: list[str] = []
    notes: list[str] = []

    gallery = repo / "src/pages/fde-demo.astro"
    if not gallery.is_file():
        errors.append(f"missing gallery: {gallery}")
        gallery_text = ""
    else:
        gallery_text = gallery.read_text(encoding="utf-8")
        expected_href = f'/fde-demo/{args.slug}'
        if expected_href not in gallery_text:
            errors.append(f"gallery does not reference {expected_href}")
        if args.title not in gallery_text:
            errors.append(f"gallery does not contain title: {args.title}")
        if "demo-card-link" not in gallery_text:
            errors.append("gallery is missing whole-card link markup")

    candidates = [
        repo / f"src/pages/fde-demo/{args.slug}.astro",
        repo / f"public/fde-demo/{args.slug}/index.html",
    ]
    sources = [path for path in candidates if path.exists()]
    if not sources:
        errors.append("missing Demo source; expected Astro route or public index.html")

    scanned = []
    network_hits = []
    for source in sources:
        root = source if source.is_dir() else source.parent
        for file in text_files(root):
            scanned.append(file)
            text = file.read_text(encoding="utf-8", errors="replace")
            for label, pattern in NETWORK_PATTERNS.items():
                if pattern.search(text):
                    network_hits.append(f"{file.relative_to(repo)}: {label}")

    if args.mode == "replay" and network_hits:
        errors.append("Replay contains network-capable content: " + "; ".join(network_hits))
    elif args.mode == "live":
        notes.extend("Live network evidence: " + hit for hit in network_hits)

    if args.dist:
        built = [
            repo / f"dist/fde-demo/{args.slug}/index.html",
            repo / f"dist/fde-demo/{args.slug}.html",
        ]
        if not any(path.is_file() for path in built):
            errors.append("built Demo output is missing from dist")
        if not (repo / "dist/fde-demo/index.html").is_file():
            errors.append("built FDE gallery output is missing")

    print(f"repo={repo}")
    print(f"slug={args.slug} mode={args.mode} scanned_files={len(set(scanned))}")
    for note in notes:
        print(f"NOTE {note}")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        return 1
    print("status=ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
