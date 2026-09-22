"""Minimal preflight and recording command builder for real logged-in sites.

Examples:
  python record_ready.py preflight --site feishu
  python record_ready.py start --site feishu --script basic --mode live --browser <id>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITES = json.loads((ROOT / "sites.json").read_text(encoding="utf-8"))
SCRIPTS = {
    "basic": "导航、搜索、筛选、打开详情、返回；不写入、不发布、不交易。",
    "data": "读取当前可见且有权访问的信息，结构化记录来源；不绕过权限/验证码/反爬。",
    "reply": "读取真实新消息，运行 Jev gate，填入候选回复；默认停在发送前人工确认。",
}


def bsk_status() -> tuple[bool, str]:
    try:
        result = subprocess.run(["bsk", "status", "--json"], capture_output=True, text=True, timeout=20)
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        return False, f"bsk_unavailable:{type(error).__name__}"
    if result.returncode != 0:
        return False, "bsk_status_failed"
    try:
        payload = json.loads(result.stdout)
        browsers = payload.get("browsers", [])
        count = len(browsers) if isinstance(browsers, list) else int(payload.get("browsers_connected", browsers))
        return count > 0, f"browsers_connected={count}"
    except (TypeError, ValueError, json.JSONDecodeError):
        return "browsers connected 0" not in result.stdout.lower(), "status_text_observed"


def record_command(site: str, script: str, mode: str, browser: str) -> str:
    target = SITES[site]
    purpose = f"[{mode.upper()}][{site.upper()}][{script.upper()}] {SCRIPTS[script]}"
    output = f"recordings/{site}-{script}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    return (
        f"bsk record start --browser {browser} --url {target['url']} "
        f"--purpose {json.dumps(purpose, ensure_ascii=False)} --redact-values --output {output}"
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--site", choices=sorted(SITES), default="feishu")
    start = sub.add_parser("start")
    start.add_argument("--site", choices=sorted(SITES), default="feishu")
    start.add_argument("--script", choices=sorted(SCRIPTS), default="basic")
    start.add_argument("--mode", choices=["live", "replay"], default="live")
    start.add_argument("--browser", required=True, help="bsk browsers 输出的 browser instance id/label")
    args = parser.parse_args()

    if args.command == "preflight":
        site = SITES[args.site]
        connected, detail = bsk_status()
        result = {
            "site": args.site,
            "label": site["label"],
            "mode": "LIVE",
            "browser_connected": connected,
            "detail": detail,
            "url": site["url"],
            "preflight": site["preflight"],
            "record_ready": connected,
            "next": "bsk browsers，然后运行 start 命令" if connected else "连接 browser-skill 扩展并重新运行本命令",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if connected else 2)

    print(record_command(args.site, args.script, args.mode, args.browser))
    print("完成后必须保留 bsk trace bundle；发送脚本只能停在发送前人工确认。")


if __name__ == "__main__":
    main()
