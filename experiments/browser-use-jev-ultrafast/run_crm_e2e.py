"""Run a no-credential 4S CRM E2E through the upstream Jev Ultrafast browser loop.

Run from the repository root with:
  uv run --project .tmp/jev-ultrafast python experiments/browser-use-jev-ultrafast/run_crm_e2e.py

The model decisions and text generation are deterministic offline stubs. The
real upstream Agent, Browser, DOM snapshot, freshness guard, and Browser
Harness-backed Chrome execution are still exercised. No paid API is called.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent
GOAL = "找到张先生，把线索阶段改为高意向，添加询价与周六试驾备注，创建周六15:00试驾跟进。"
NOTE = "客户询价；周六试驾"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def choose_offline(page, _goal, history):
    """Select only from the current DOM actions, like a bounded model result."""
    actions = page["actions"]
    stage_saved = any(item.get("action") == "保存阶段" for item in history)
    note_added = any(item.get("action") == "添加备注" for item in history)
    followup_created = any(item.get("action") == "创建跟进" for item in history)
    def pick(kind, text):
        for action in actions:
            if action["kind"] == kind and text in action["label"]:
                return action
        return None

    def pick_exact(kind, label):
        for action in actions:
            if action["kind"] == kind and action["label"] == label:
                return action
        return None

    # The priority is the task flow, not a selector: every choice is resolved
    # against the current observed action table before execution.
    action = pick("fill", "线索搜索")
    if action and not action.get("value"):
        operation = "TYPE_TEXT"
        target = "1"
    else:
        action = pick_exact("click", "搜索")
        if action and "李女士" not in page["text"]:
            action = None
        if action:
            operation = "CLICK"
            target = "1"
        else:
            action = pick("click", "查看张先生")
            if action:
                operation = "CLICK"
                target = "1"
            else:
                action = None if stage_saved else pick("select", "高意向")
                if action:
                    operation = "SELECT"
                    target = "1:1"
                else:
                    action = None if stage_saved else pick("click", "保存阶段")
                    if action:
                        operation = "CLICK"
                        target = "1"
                    else:
                        action = None if note_added else pick("fill", "备注内容")
                        if action and not action.get("value"):
                            operation = "TYPE_TEXT"
                            target = "1"
                        else:
                            action = None if note_added else pick("click", "添加备注")
                            if action:
                                operation = "CLICK"
                                target = "1"
                            else:
                                action = None if followup_created else pick("select", "试驾")
                                if action:
                                    operation = "SELECT"
                                    target = "1:1"
                                else:
                                    action = None if followup_created else pick("select", "周六")
                                    if action:
                                        operation = "SELECT"
                                        target = "2:1"
                                    else:
                                        action = None if followup_created else pick("select", "15:00")
                                        if action:
                                            operation = "SELECT"
                                            target = "3:1"
                                        else:
                                            action = None if followup_created else pick("click", "创建跟进")
                                            if action:
                                                operation = "CLICK"
                                                target = "1"
                                            elif stage_saved and note_added and followup_created:
                                                selected = "DONE"
                                                return {
                                                    "choice": selected,
                                                    "operation": selected,
                                                    "target": None,
                                                    "confidence": 1.0,
                                                    "probabilities": {selected: 1.0},
                                                    "operation_probabilities": {selected: 1.0},
                                                    "target_probabilities": {},
                                                    "target_confidence": None,
                                                    "raw_answers": {},
                                                    "model": "offline-deterministic-stub",
                                                    "usage": {},
                                                    "latency_ms": 0,
                                                    "request": {"offline": True},
                                                }
                                            else:
                                                action = pick("scroll", "Scroll down")
                                                if action:
                                                    operation = "SCROLL_DOWN"
                                                    target = None
                                                else:
                                                    raise AssertionError(
                                                        "No deterministic action matched the observed CRM page: "
                                                        + json.dumps(
                                                            {"actions": page["actions"], "history": history},
                                                            ensure_ascii=False,
                                                        )
                                                    )

    selected = action["id"]
    return {
        "choice": selected,
        "operation": operation,
        "target": target,
        "confidence": 1.0,
        "probabilities": {selected: 1.0},
        "operation_probabilities": {operation: 1.0},
        "target_probabilities": {target: 1.0},
        "target_confidence": 1.0,
        "raw_answers": {},
        "model": "offline-deterministic-stub",
        "usage": {},
        "latency_ms": 0,
        "request": {"offline": True, "goal": GOAL},
    }


def text_offline(context):
    field = context["field"]["label"]
    if field == "线索搜索":
        value = "张先生"
    elif field == "备注内容":
        value = NOTE
    else:
        raise AssertionError(f"Unexpected text field: {field}")
    return value, {"model": "offline-deterministic-stub", "latency_ms": 0, "usage": {}}


def run(jev_root: Path, *, live: bool = False) -> dict:
    if not (jev_root / "jev_ultrafast" / "agent.py").is_file():
        raise FileNotFoundError(f"jev-ultrafast checkout not found: {jev_root}")
    if live:
        missing = [name for name in ("TYPESAFE_API_KEY", "TEXT_MODEL_API_KEY") if not os.getenv(name)]
        if missing:
            raise RuntimeError("Live CRM mode is blocked; missing environment entries: " + ", ".join(missing))
    sys.path.insert(0, str(jev_root))
    from jev_ultrafast import agent as loop

    original_choose, original_text = loop.choose, loop.field_text
    if not live:
        loop.choose, loop.field_text = choose_offline, text_offline
    handler = partial(QuietHandler, directory=str(FIXTURE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/crm.html"
    trace = []
    try:
        with loop.Agent(url, GOAL) as agent:
            for state in agent.run():
                history = state["history"]
                trace.append(
                    {
                        "status": state["status"],
                        "actions": len(history),
                        "last_action": history[-1]["action"] if history else None,
                        "page": state["page"]["url"],
                        "live_readback": agent.browser.evaluate("window.crmReadback()"),
                    }
                )
                if len(history) > 20:
                    raise AssertionError(
                        "CRM flow exceeded the bounded 20-action budget: "
                        + json.dumps(trace, ensure_ascii=False)
                    )
            readback = agent.browser.evaluate("window.crmReadback()")
            assert readback["selectedLeadId"] == "lead-zhang", json.dumps(
                {"readback": readback, "trace": trace}, ensure_ascii=False
            )
            lead = next(item for item in readback["leads"] if item["id"] == "lead-zhang")
            assert lead["stage"] == "高意向", json.dumps(
                {"readback": readback, "trace": trace}, ensure_ascii=False
            )
            assert NOTE in lead["notes"], json.dumps(
                {"readback": readback, "trace": trace}, ensure_ascii=False
            )
            assert {"type": "试驾", "day": "周六", "time": "15:00"} in lead["followups"], json.dumps(
                {"readback": readback, "trace": trace}, ensure_ascii=False
            )
            assert agent.state["status"] == "done"
            return {
                "mode": "live" if live else "offline-deterministic-stub",
                "live_api_calls": None if live else 0,
                "browser_url": url,
                "agent_status": agent.state["status"],
                "actions": len(agent.state["history"]),
                "decisions": len(agent.state["decisions"]),
                "readback": readback,
                "trace": trace,
            }
    finally:
        if not live:
            loop.choose, loop.field_text = original_choose, original_text
        server.shutdown()
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--jev-root",
        type=Path,
        default=ROOT / ".tmp" / "jev-ultrafast",
        help="isolated browser-use/jev-ultrafast checkout (default: .tmp/jev-ultrafast)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="use real Jev and text-provider calls; never falls back to offline stubs",
    )
    args = parser.parse_args()
    result = run(args.jev_root.resolve(), live=args.live)
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
