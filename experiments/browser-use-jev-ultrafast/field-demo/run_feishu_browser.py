"""Run the three Feishu field scenarios through the real Jev Ultrafast browser loop.

The user's camera records the visible browser window. This program is the
browser automation: Agent/TypeSafe chooses actions, Browser executes them, and
this runner blocks send/publish/trade actions. It never logs in or bypasses a
captcha. C fills a candidate reply and stops before send.

Run from the repository root with the isolated upstream environment:
  uv run --project .tmp/jev-ultrafast python \
    experiments/browser-use-jev-ultrafast/field-demo/run_feishu_browser.py \
    --scenario A --query "项目关键词"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
JEV_ROOT = ROOT / ".tmp" / "jev-ultrafast"
FIELD_ROOT = Path(__file__).resolve().parent
DEFAULT_URL = "https://www.feishu.cn/"
FORBIDDEN_WORDS = ("发送", "发布", "交易", "购买", "付款", "下单")


def activate_visible_target(browser: Any) -> None:
    """Make the owned Browser Harness target visible for the user's camera."""
    from browser_harness.helpers import cdp

    cdp("Target.activateTarget", targetId=browser.target)


def action_label(page: dict[str, Any], action_id: str) -> str:
    for action in page.get("actions", []):
        if action.get("id") == action_id:
            return str(action.get("label", action_id))
    return action_id


def safe_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep action evidence without raw message/page/model payloads."""
    return [
        {
            "step": item.get("step"),
            "action": item.get("action"),
            "kind": item.get("kind"),
            "page_changed": item.get("page_changed"),
            "url": item.get("url"),
        }
        for item in history
    ]


def write_evidence(scenario: str, payload: dict[str, Any], output_root: Path | None) -> Path:
    directory = output_root or (ROOT / "field-recordings")
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"feishu-{scenario.lower()}-{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def fixed_field_text(context: dict[str, Any], query: str, candidate: str | None = None) -> tuple[str, dict[str, Any]]:
    """Use only explicit operator input; do not invoke TEXT_MODEL_API_KEY."""
    label = str(context.get("field", {}).get("label", ""))
    if query and any(word in label for word in ("搜索", "查找", "Search", "search")):
        return query, {"model": "operator-provided", "latency_ms": 0, "usage": {}}
    if candidate and any(word in label for word in ("回复", "消息", "输入", "Reply", "reply")):
        return candidate, {"model": "jev-template", "latency_ms": 0, "usage": {}}
    raise RuntimeError(f"No explicit safe text is available for field {label!r}; nothing was typed.")


def run_guarded_agent(agent: Any, goal: str, query: str, candidate: str | None = None) -> dict[str, Any]:
    """Let real Jev choose observed actions, but reject irreversible actions before act()."""
    import jev_ultrafast.agent as agent_module

    original_text = agent_module.field_text
    agent_module.field_text = lambda context: fixed_field_text(context, query, candidate)
    try:
        trace: list[dict[str, Any]] = []
        while agent.state["status"] not in {"done", "blocked"}:
            agent.command("predict")
            decision = agent.state["decision"]
            label = action_label(agent.state["page"], decision["choice"])
            trace.append(
                {
                    "event": "decision",
                    "operation": decision.get("operation"),
                    "action": label,
                    "allowed": not any(word in label for word in FORBIDDEN_WORDS),
                }
            )
            if any(word in label for word in FORBIDDEN_WORDS):
                agent.state["decision"] = None
                agent.state["status"] = "blocked"
                trace[-1]["blocked_reason"] = "irreversible action requires separate human authorization"
                break
            agent.command("act", {"fingerprint": agent.state["page"]["fingerprint"]})
            if len(agent.state["history"]) > 20:
                agent.state["status"] = "blocked"
                trace.append({"event": "blocked", "blocked_reason": "20-action safety budget"})
                break
        return {"status": agent.state["status"], "trace": trace}
    finally:
        agent_module.field_text = original_text


def scenario_goal(scenario: str, query: str) -> str:
    if scenario == "A":
        return (
            f"在当前网页版飞书中完成基础操作：使用搜索入口搜索“{query}”，使用一个当前可见的筛选，"
            "打开一个搜索结果详情，再返回结果页。只导航和读取，不发送、不发布、不交易；满足后停止。"
        )
    if scenario == "B":
        return (
            f"在当前网页版飞书中搜索并打开与“{query}”相关的、用户有权访问的一个详情页。"
            "停在详情页读取当前可见内容，保持只读，不发送、不发布、不交易；找到详情后停止。"
        )
    return (
        "在当前网页版飞书中打开消息入口，找到一条最新可见消息并打开会话详情。"
        "只读取消息，不发送、不发布、不交易；打开消息详情后停止。"
    )


def candidate_for(decision: dict[str, Any]) -> str:
    if decision["next_action"] == "no_contact":
        return "已收到你的选择。我们会尊重你的意愿，不再主动联系。"
    if decision["next_action"] == "collect_evidence":
        return "已收到。为了准确帮助你，请补充希望了解的产品、时间或具体问题。"
    return "已收到你的消息。我会先记录需求，并由人工确认后回复你。"


def run(
    scenario: str,
    url: str,
    query: str,
    output_root: Path | None,
    allow_visible_data: bool,
    goal_override: str | None = None,
) -> dict[str, Any]:
    if not (JEV_ROOT / "jev_ultrafast" / "agent.py").is_file():
        raise FileNotFoundError(f"isolated jev-ultrafast checkout not found: {JEV_ROOT}")
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise RuntimeError("TYPESAFE_API_KEY missing; real Jev browser decisions cannot run")
    sys.path.insert(0, str(JEV_ROOT))
    from jev_ultrafast.agent import Agent
    from jev_ultrafast.browser import StalePage
    from reply_gate import live as live_reply_gate

    goal = goal_override or scenario_goal(scenario, query)
    result: dict[str, Any] = {
        "mode": "LIVE",
        "scenario": scenario,
        "url": url,
        "camera_recording": "operator-owned-camera",
        "browser_automation": "jev_ultrafast.Agent + Browser + live TypeSafe Jev",
        "send_clicked": False,
        "publish_clicked": False,
        "trade_clicked": False,
    }
    with Agent(url, goal, screenshots=False) as agent:
        activate_visible_target(agent.browser)
        run_result = run_guarded_agent(agent, goal, query)
        result["agent_status"] = run_result["status"]
        result["decisions"] = run_result["trace"]
        result["actions"] = safe_history(agent.state["history"])
        page = agent.state["page"]
        result["page"] = {"url": page.get("url"), "title": page.get("title"), "visible_text_chars": len(page.get("text", ""))}

        if scenario == "B":
            visible_lines = [line.strip() for line in page.get("text", "").splitlines() if line.strip()]
            result["visible_data"] = {
                "source": page.get("url"),
                "title": page.get("title"),
                "observed_at": datetime.now(timezone.utc).isoformat(),
                "visible_text_chars": len(page.get("text", "")),
                "visible_lines": visible_lines[:80] if allow_visible_data else [],
                "lines_omitted": max(0, len(visible_lines) - 80) if allow_visible_data else len(visible_lines),
            }
            if allow_visible_data:
                print(json.dumps(result["visible_data"], ensure_ascii=False, indent=2))
        elif scenario == "C":
            visible_message = page.get("text", "").strip()
            if not visible_message:
                raise RuntimeError("No visible message text was observed; no reply decision or browser mutation made.")
            decision = live_reply_gate(visible_message[:6000])
            candidate = candidate_for(decision)
            result["reply_decision"] = {
                key: decision.get(key)
                for key in ("intent", "risk", "next_action", "human_needed", "model")
            }
            result["candidate_template_created"] = True
            reply_action = next(
                (
                    action
                    for action in page.get("actions", [])
                    if action.get("kind") == "fill"
                    and any(word in str(action.get("label", "")) for word in ("回复", "消息", "输入", "Reply", "reply"))
                ),
                None,
            )
            if reply_action is None:
                result["reply_filled"] = False
                result["blocked_reason"] = "reply input was not a stable observed control"
            else:
                if any(word in str(reply_action.get("label", "")) for word in FORBIDDEN_WORDS):
                    raise StalePage("Refused a control labelled as irreversible.")
                agent.browser.act(reply_action, page, text=candidate)
                agent.browser.observe(screenshot=False)
                result["reply_filled"] = True
                result["candidate_length"] = len(candidate)
            result["human_confirmation_required"] = True
            result["send_allowed"] = False
    evidence = write_evidence(scenario, result, output_root)
    result["evidence_file"] = str(evidence)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--scenario", choices=["A", "B", "C"])
    prompt_group.add_argument("--prompt", help="直接交给 Agent 的完整提示词；不要包含密码、验证码或 Token")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--query", default="项目协作", help="A/B 的人工指定搜索词；不会从环境变量猜测")
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--allow-visible-data", action="store_true", help="B 场景明确允许把当前可见文本结构化输出")
    args = parser.parse_args()
    scenario = args.scenario or "A"
    payload = run(
        scenario,
        args.url,
        args.query,
        args.output_root,
        args.allow_visible_data,
        goal_override=args.prompt,
    )
    sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
