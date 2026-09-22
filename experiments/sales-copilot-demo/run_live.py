"""Run the real three-round 4S scenario and save redacted evidence.

The caller must inject TYPESAFE_API_KEY into this process. The script never
prints or writes the key; only Jev response metadata, typed answers, and test
CRM readback are saved.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from domain import TestCRM, apply_approval, build_proposal
from live_client import LiveAPIError, evaluate_live

ROOT = Path(__file__).resolve().parent


def load_cases() -> dict[str, dict]:
    return {case["id"]: case for case in json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]}


def one_round(case: dict | None, message: str, round_id: str, crm: TestCRM) -> dict:
    try:
        decision = evaluate_live(case, message, round_id)
    except LiveAPIError as error:
        return {"status": "live_error", "round_id": round_id, "http_status": error.status, "error_type": error.error_type, "request_id": error.request_id or "unavailable", "no_mutation": True}
    proposal = build_proposal(decision, case, crm.snapshot())
    return {"status": "ok", "decision": decision, "proposal": proposal}


def run(output: Path) -> dict:
    cases = load_cases()
    crm = TestCRM()
    positive = cases["high_intent_i3"]
    cancel = cases["cancel_no_contact"]
    positive_result = one_round(positive, positive["message"], "live-positive-1", crm)
    approval = None
    if positive_result["status"] == "ok":
        proposal = positive_result["proposal"]
        approval = apply_approval(
            crm,
            proposal,
            customer_confirmed=True,
            idempotency_key="live-positive-1-human-confirmation",
            expected_epoch=proposal["epoch"],
            expected_revision=proposal["revision"],
        )
    cancel_result = one_round(cancel, cancel["message"], "live-cancel-1", crm)
    unknown_message = "临时输入：预算还没定，周六先看看再说，别当我已经订车。"
    unknown_result = one_round(None, unknown_message, "live-unknown-1", crm)
    evidence = {
        "mode": "live",
        "claim_boundary": "模拟销售场景；真实 Jev 请求；人工确认后只写入测试 CRM；不代表真实预约成功",
        "rounds": {
            "positive": positive_result,
            "positive_human_approval": approval,
            "cancel_no_contact": cancel_result,
            "temporary_unknown": unknown_result,
        },
        "crm_readback_after_positive": crm.snapshot(),
        "no_real_booking_system": True,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "evidence" / "live-evidence.json")
    args = parser.parse_args()
    result = run(args.output)
    summary = {
        "status": "pass" if all(result["rounds"][name]["status"] == "ok" for name in ("positive", "cancel_no_contact", "temporary_unknown")) else "partial",
        "mode": result["mode"],
        "rounds": {name: {"status": value["status"], "model": value.get("decision", {}).get("model"), "request_id": value.get("decision", {}).get("request_id"), "latency_ms": value.get("decision", {}).get("latency_ms"), "error_type": value.get("error_type")} for name, value in result["rounds"].items() if isinstance(value, dict)},
        "evidence": str(args.output),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
