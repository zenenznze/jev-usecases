"""Start one real browser-skill recording for the field scripts.

The browser remains user-controlled. This command only starts bsk's trace
recorder; it never logs in, sends, publishes, trades, or reads credentials.

Example:
  python start_recording.py --script basic --browser <browser-id> --run
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "record_scripts"

SCRIPT_META = {
    "basic": {"title": "Feishu A 基础操作", "file": "01_feishu_basic.md"},
    "data": {"title": "Feishu B 可见数据读取", "file": "02_feishu_visible_data.md"},
    "reply": {"title": "Feishu C 实时回复（发送前）", "file": "03_feishu_reply_before_send.md"},
}


def build_command(script: str, mode: str, browser: str, output: Path) -> list[str]:
    purpose = f"[{mode.upper()}][FEISHU][{script.upper()}] {SCRIPT_META[script]['title']}"
    return [
        "bsk",
        "record",
        "start",
        "--browser",
        browser,
        "--url",
        "https://www.feishu.cn/",
        "--purpose",
        purpose,
        "--redact-values",
        "--output",
        str(output),
    ]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", choices=sorted(SCRIPT_META), required=True)
    parser.add_argument("--browser", required=True, help="bsk browsers 输出的 browser instance id/label")
    parser.add_argument("--mode", choices=["live", "replay"], default="live")
    parser.add_argument("--run", action="store_true", help="直接启动 bsk record；不加则只打印可审阅命令")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = Path("recordings") / f"feishu-{args.script}-{args.mode}-{stamp}"
    command = build_command(args.script, args.mode, args.browser, output)
    print(json.dumps({"mode": args.mode.upper(), "script": SCRIPT_META[args.script], "trace_output": str(output)}, ensure_ascii=False, indent=2))
    print("脚本步骤：", SCRIPTS / SCRIPT_META[args.script]["file"])
    print("启动命令：", subprocess.list2cmdline(command))
    print("安全边界：发送/发布/交易保持停止；登录、验证码、风控由用户人工接管。")
    if args.run:
        raise SystemExit(subprocess.run(command, check=False).returncode)


if __name__ == "__main__":
    main()
