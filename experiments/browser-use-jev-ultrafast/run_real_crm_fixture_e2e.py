"""Complete the CRM browser path with real Jev plus fixture-supplied text.

Run with TYPESAFE_API_KEY injected into this child:
  uv run --project .tmp/jev-ultrafast python experiments/browser-use-jev-ultrafast/run_real_crm_fixture_e2e.py

Real Jev chooses search/open/stage/save. The text model is unavailable, so
this harness supplies the exact task text as fixture input to the real Browser
executor, then independently reads CRM state. It never claims LLM text output.
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
EVIDENCE = ROOT / ".tmp" / "real-crm-fixture-e2e.json"
STAGE_GOAL = "找到张先生，把线索阶段改为高意向并保存阶段，完成后停止。"
NOTE_TEXT = "客户询价；周六试驾"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def execute_visible(browser, kind: str, phrase: str, *, text: str | None = None) -> dict:
    """Execute an observed action, scrolling only through observed controls."""
    for _ in range(8):
        page = browser.observe()
        action = next(
            (
                item
                for item in page["actions"]
                if item["kind"] == kind and phrase in item["label"]
            ),
            None,
        )
        if action is not None:
            browser.act(action, page, text=text)
            return {"kind": kind, "intent": phrase}
        scroll = next((item for item in page["actions"] if item["id"] == "scroll_down"), None)
        if scroll is None:
            raise AssertionError(
                json.dumps(
                    {"missing_kind": kind, "missing_phrase": phrase, "actions": page["actions"]},
                    ensure_ascii=False,
                )
            )
        browser.act(scroll, page)
    raise AssertionError(f"Could not expose observed action: {kind} {phrase}")


def run(jev_root: Path) -> dict:
    if not os.getenv("TYPESAFE_API_KEY"):
        raise RuntimeError("TYPESAFE_API_KEY is missing; real Jev CRM path cannot run.")
    if not (jev_root / "jev_ultrafast" / "agent.py").is_file():
        raise FileNotFoundError(f"jev-ultrafast checkout not found: {jev_root}")

    sys.path.insert(0, str(jev_root))
    from jev_ultrafast import Agent

    handler = partial(QuietHandler, directory=str(FIXTURE_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/crm.html"
    browser_steps: list[dict] = []
    try:
        with Agent(url, STAGE_GOAL) as agent:
            initial = agent.state["page"]
            search = next(
                action
                for action in initial["actions"]
                if action["kind"] == "fill" and action["label"] == "线索搜索"
            )
            # Fixture precondition: remove the text-model dependency from search.
            agent.browser.act(search, initial, text="张先生")
            agent.state["page"] = agent.browser.observe()
            agent.state["history"].append(
                {
                    "step": 0,
                    "action": "fixture prefill: 线索搜索",
                    "kind": "fill",
                    "text": "张先生",
                    "page_changed": True,
                }
            )

            for state in agent.run():
                if len(state["history"]) > 20:
                    raise AssertionError("Real Jev stage path exceeded the bounded action budget")
            if agent.state["status"] != "done":
                raise AssertionError(f"Real Jev stage path ended as {agent.state['status']}")

            browser_steps.append(execute_visible(agent.browser, "fill", "备注内容", text=NOTE_TEXT))
            browser_steps.append(execute_visible(agent.browser, "click", "添加备注"))
            browser_steps.append(execute_visible(agent.browser, "select", "试驾"))
            browser_steps.append(execute_visible(agent.browser, "select", "周六"))
            browser_steps.append(execute_visible(agent.browser, "select", "15:00"))
            browser_steps.append(execute_visible(agent.browser, "click", "创建跟进"))

            readback = agent.browser.evaluate("window.crmReadback()")
            lead = next(item for item in readback["leads"] if item["id"] == "lead-zhang")
            expected_followup = {"type": "试驾", "day": "周六", "time": "15:00"}
            assert readback["selectedLeadId"] == "lead-zhang", readback
            assert lead["stage"] == "高意向", readback
            assert NOTE_TEXT in lead["notes"], readback
            assert expected_followup in lead["followups"], readback
            result = {
                "mode": "real-jev-plus-fixture-text-browser",
                "type_safe_decisions": len(agent.state["decisions"]),
                "text_api_calls": 0,
                "fixture_text_inputs": [NOTE_TEXT],
                "browser_steps_after_jev": browser_steps,
                "readback": readback,
            }
            EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
            EVIDENCE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return result
    finally:
        server.shutdown()
        server.server_close()


def main() -> None:
    result = run((ROOT / ".tmp" / "jev-ultrafast").resolve())
    sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
