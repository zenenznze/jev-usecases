"""Run the real Jev decision path for CRM actions that do not need a text model.

Run from the repository root with TYPESAFE_API_KEY injected into this child:
  uv run --project .tmp/jev-ultrafast python experiments/browser-use-jev-ultrafast/run_jev_only_probe.py

The search value is pre-seeded as a fixture precondition. Jev must still choose
and execute the search, customer, stage, and save actions. The probe stops
before any TYPE_TEXT note action and never substitutes a text-model stub.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent
EVIDENCE = ROOT / ".tmp" / "jev-only-latest.json"
GOAL = "找到张先生，把线索阶段改为高意向并保存阶段，完成后停止。"
QUERY = "张先生"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def run(jev_root: Path) -> dict:
    if not os.getenv("TYPESAFE_API_KEY"):
        raise RuntimeError("TYPESAFE_API_KEY is missing; real Jev probe cannot run.")
    if not (jev_root / "jev_ultrafast" / "agent.py").is_file():
        raise FileNotFoundError(f"jev-ultrafast checkout not found: {jev_root}")

    sys.path.insert(0, str(jev_root))
    from jev_ultrafast import Agent

    handler = partial(QuietHandler, directory=str(FIXTURE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/crm.html"
    try:
        with Agent(url, GOAL) as agent:
            initial = agent.state["page"]
            search = next(
                action
                for action in initial["actions"]
                if action["kind"] == "fill" and action["label"] == "线索搜索"
            )
            # This is fixture setup only. It removes the text-model dependency
            # so the following operations are decided by the real Jev model.
            agent.browser.act(search, initial, text=QUERY)
            agent.state["page"] = agent.browser.observe()
            agent.state["history"].append(
                {
                    "step": 0,
                    "action": "fixture prefill: 线索搜索",
                    "kind": "fill",
                    "text": QUERY,
                    "page_changed": True,
                }
            )

            trace = []
            for _ in range(20):
                state = agent.command("predict")
                decision = state["decision"]
                choice = decision["choice"]
                if choice in {"DONE", "BLOCKED"}:
                    trace.append({"status": choice.lower(), "operation": decision["operation"]})
                    break
                action = next(item for item in state["page"]["actions"] if item["id"] == choice)
                if action["kind"] == "fill":
                    raise RuntimeError(
                        "Real Jev requested TYPE_TEXT; text-model probe is correctly stopped without a guess."
                    )
                agent.command("act", {"fingerprint": state["page"]["fingerprint"]})
                trace.append(
                    {
                        "status": "executed",
                        "action": action["label"],
                        "kind": action["kind"],
                        "operation": decision["operation"],
                    }
                )
            else:
                raise RuntimeError("Real Jev CRM probe exceeded the 20-decision bound.")

            readback = agent.browser.evaluate("window.crmReadback()")
            lead = next(item for item in readback["leads"] if item["id"] == "lead-zhang")
            if readback["selectedLeadId"] != "lead-zhang" or lead["stage"] != "高意向":
                raise AssertionError(
                    json.dumps({"readback": readback, "trace": trace}, ensure_ascii=False)
                )
            return {
                "mode": "real-jev-no-text",
                "text_api_calls": 0,
                "type_safe_decisions": len(agent.state["decisions"]),
                "readback": readback,
                "trace": trace,
            }
    finally:
        server.shutdown()
        server.server_close()


def main() -> None:
    jev_root = ROOT / ".tmp" / "jev-ultrafast"
    result = run(jev_root.resolve())
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(payload, encoding="utf-8")
    sys.stdout.buffer.write(payload.encode("utf-8"))


if __name__ == "__main__":
    main()
