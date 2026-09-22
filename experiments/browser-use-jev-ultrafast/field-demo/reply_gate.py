"""Jev reply gate: classify a user-supplied visible message, never send.

Live mode uses the real Jev endpoint and only the User-level TYPESAFE_API_KEY
in the child environment. It produces a candidate template and a hard
send=false result; the operator must fill the site composer and manually review.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JEV_ROOT = ROOT / ".tmp" / "jev-ultrafast"


def replay(message: str) -> dict:
    lower = message.lower()
    if any(word in message for word in ("不要联系", "别联系", "勿扰")):
        return {"intent": "no_contact", "risk": "low", "next_action": "no_contact", "human_needed": False}
    if len(message.strip()) < 8 or message.strip() in {"再看看", "嗯", "好的"}:
        return {"intent": "insufficient_evidence", "risk": "unknown", "next_action": "collect_evidence", "human_needed": True}
    return {"intent": "sales_inquiry", "risk": "needs_confirmation", "next_action": "human_review", "human_needed": True}


def live(message: str) -> dict:
    if not os.getenv("TYPESAFE_API_KEY"):
        raise RuntimeError("TYPESAFE_API_KEY missing; live Jev gate cannot run")
    sys.path.insert(0, str(JEV_ROOT))
    from jev_ultrafast.model import post_json

    result = post_json(
        "https://api.typesafe.ai/v1/systemone",
        os.environ["TYPESAFE_API_KEY"],
        {
            "model": os.environ.get("TYPESAFE_MODEL", "jev-latest"),
            "state": {"visible_message": message},
            "questions": {
                "intent": {
                    "type": "choice",
                    "criteria": {
                        "sales_inquiry": "询价、试驾、购买或产品信息",
                        "no_contact": "明确拒绝联系或要求停止消息",
                        "other": "其他或无法判断",
                    },
                    "instructions": "判断当前可见消息的主要意图。",
                },
                "risk": {
                    "type": "choice",
                    "criteria": {
                        "low": "没有明显风险",
                        "needs_confirmation": "需要人工确认后再回复",
                        "unknown": "证据不足，不能安全判断",
                    },
                    "instructions": "判断回复风险。",
                },
                "next_action": {
                    "type": "choice",
                    "criteria": {
                        "human_review": "转人工审核",
                        "collect_evidence": "先补充信息",
                        "no_contact": "停止主动联系",
                    },
                    "instructions": "选择下一动作，不执行发送。",
                },
                "human_needed": {"type": "noul", "instructions": "回复前需要人工确认。"},
            },
        },
    )
    answers = result.get("answers", {})
    return {
        "intent": answers["intent"]["choice"],
        "risk": answers["risk"]["choice"],
        "next_action": answers["next_action"]["choice"],
        "human_needed": float(answers["human_needed"]["noul"]) >= 0.5,
        "model": result.get("model"),
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True, help="人工从当前页面复制的可见消息；不要粘贴凭据")
    parser.add_argument("--source", required=True, help="来源站点/页面说明，不填 Cookie 或 Token")
    parser.add_argument("--mode", choices=["live", "replay"], default="live")
    args = parser.parse_args()
    decision = live(args.message) if args.mode == "live" else replay(args.message)
    if decision["next_action"] == "no_contact":
        template = "已收到你的选择。我们会尊重你的意愿，不再主动联系。"
    elif decision["next_action"] == "collect_evidence":
        template = "已收到。为了准确帮助你，请补充希望了解的产品、时间或具体问题。"
    else:
        template = "已收到你的消息。我会先记录需求，并由人工确认后回复你。"
    print(
        json.dumps(
            {
                "mode": args.mode.upper(),
                "source": args.source,
                "decision": decision,
                "candidate_template": template,
                "send_allowed": False,
                "human_confirmation_required": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
