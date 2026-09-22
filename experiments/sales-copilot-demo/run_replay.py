"""Run the deterministic acceptance suite and write sanitized replay evidence.

Command: python run_replay.py
No credential and no network are used.
"""

from __future__ import annotations

import json
from pathlib import Path

from domain import TestCRM, apply_approval, build_proposal, fingerprint, replay_decision, visible_network_error

ROOT = Path(__file__).resolve().parent


def load_cases() -> list[dict]:
    return json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]


def run() -> dict:
    cases = load_cases()
    by_id = {case["id"]: case for case in cases}
    case_results = []
    stage_scored = 0
    stage_matches = 0
    high_value_total = 0
    high_value_hits = 0
    risk_total = 0
    risk_human_hits = 0
    wrong_progressions = 0

    for case in cases:
        decision = replay_decision(case, case["message"], "replay-case-" + case["id"])
        proposal = build_proposal(decision, case, TestCRM().snapshot())
        selected_stage = decision["answers"]["lead_stage"]["choice"]
        expected_stage = case["gold"]["lead_stage"]
        if expected_stage in {"awareness", "consideration", "evaluation", "ready"}:
            stage_scored += 1
            stage_matches += int(selected_stage == expected_stage)
        high_value_total += int(case["gold"]["high_value_lead"])
        high_value_hits += int(case["gold"]["high_value_lead"] and decision["answers"]["high_value_lead"]["noul"] >= 0.70)
        risk_total += int(case["gold"]["risk_to_human"])
        risk_human_hits += int(case["gold"]["risk_to_human"] and (proposal["action_band"] == "human" or proposal["blocked_outreach"]))
        wrong_progressions += int(not case["facts"].get("appointment_confirmed") and proposal["crm_mutation"])
        case_results.append(
            {
                "id": case["id"],
                "category": case["category"],
                "selected_stage": selected_stage,
                "expected_stage": expected_stage,
                "high_value_probability": decision["answers"]["high_value_lead"]["noul"],
                "action": proposal["action"],
                "action_band": proposal["action_band"],
                "human_needed": proposal["human_needed"],
                "wrong_progression_blocked": not proposal["crm_mutation"],
            }
        )

    crm = TestCRM()
    positive = by_id["high_intent_i3"]
    positive_decision = replay_decision(positive, positive["message"], "positive-1")
    positive_proposal = build_proposal(positive_decision, positive, crm.snapshot())
    before = crm.snapshot()
    assert positive_proposal["action"] == "await_customer_confirmation"
    assert before["records"]["lead-zhang"]["appointment"] is None
    written = apply_approval(
        crm,
        positive_proposal,
        customer_confirmed=True,
        idempotency_key="positive-1-confirmation",
        expected_epoch=positive_proposal["epoch"],
        expected_revision=positive_proposal["revision"],
    )
    assert written["status"] == "written"
    assert written["crm"]["records"]["lead-zhang"]["appointment"]["real_booking_system"] is False
    duplicate = apply_approval(
        crm,
        positive_proposal,
        customer_confirmed=True,
        idempotency_key="positive-1-confirmation",
        expected_epoch=positive_proposal["epoch"],
        expected_revision=positive_proposal["revision"],
    )
    assert duplicate["status"] == "duplicate"
    assert len(duplicate["crm"]["records"]["lead-zhang"]["notes"]) == 1

    stale_before = crm.snapshot()
    stale_decision = replay_decision(positive, positive["message"], "stale-1")
    stale_proposal = build_proposal(stale_decision, positive, stale_before)
    crm.reset()
    stale = apply_approval(
        crm,
        stale_proposal,
        customer_confirmed=True,
        idempotency_key="stale-1-confirmation",
        expected_epoch=stale_proposal["epoch"],
        expected_revision=stale_proposal["revision"],
    )
    assert stale["status"] == "stale_discarded"
    assert stale["mutated"] is False

    cancel = by_id["cancel_no_contact"]
    cancel_decision = replay_decision(cancel, cancel["message"], "cancel-1")
    cancel_proposal = build_proposal(cancel_decision, cancel, crm.snapshot())
    assert cancel_proposal["blocked_outreach"] is True
    cancel_result = apply_approval(
        crm,
        cancel_proposal,
        customer_confirmed=True,
        idempotency_key="cancel-1-confirmation",
        expected_epoch=cancel_proposal["epoch"],
        expected_revision=cancel_proposal["revision"],
    )
    assert cancel_result["status"] == "blocked"
    assert cancel_result["mutated"] is False

    unknown_message = "预算只能到三千月供，周六先看看再说，别把我的话当成订车。"
    unknown_decision = replay_decision(None, unknown_message, "unknown-1")
    unknown_proposal = build_proposal(unknown_decision, None, crm.snapshot())
    assert unknown_decision["case_id"] == "temporary_unknown"
    assert unknown_proposal["action_band"] == "human"

    evidence = {
        "mode": "replay",
        "claim_boundary": "模拟销售场景；无真实预约系统；CRM 写入是测试状态",
        "cases_total": len(cases),
        "case_results": case_results,
        "metrics": {
            "stage_accuracy_on_scored_cases": (stage_matches / stage_scored) if stage_scored else None,
            "high_value_recall": (high_value_hits / high_value_total) if high_value_total else None,
            "risk_to_human_recall": (risk_human_hits / risk_total) if risk_total else None,
            "wrong_progression_count": wrong_progressions,
            "replay_latency_ms": 0,
            "replay_token_cost": 0,
            "threshold_note": "演示门槛是起始策略，不是生产校准标准。",
        },
        "positive_flow": {
            "initial_action": positive_proposal["action"],
            "initial_crm_appointment": before["records"]["lead-zhang"]["appointment"],
            "approval_status": written["status"],
            "readback_appointment": written["crm"]["records"]["lead-zhang"]["appointment"],
            "second_same_approval": duplicate["status"],
        },
        "reverse_challenges": {
            "cancel_no_contact": {"action": cancel_proposal["action"], "approval_result": cancel_result["status"], "crm_mutated": cancel_result["mutated"]},
            "temporary_unknown_input": {"round_id": unknown_decision["round_id"], "input_fingerprint": unknown_decision["input_fingerprint"], "action": unknown_proposal["action"], "action_band": unknown_proposal["action_band"]},
            "stale_result": {"result": stale["status"], "crm_mutated": stale["mutated"]},
            "network_failure_visible": visible_network_error(ConnectionError("synthetic transport failure")),
        },
        "deterministic_checks": {
            "idempotency": True,
            "stale_discard": True,
            "no_auto_appointment": True,
            "no_contact_block": True,
            "unknown_reclassification": True,
            "failure_no_mutation": True,
        },
    }
    output = ROOT / "evidence" / "replay-evidence.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": "pass", "cases_total": result["cases_total"], "metrics": result["metrics"], "evidence": "evidence/replay-evidence.json"}, ensure_ascii=True, indent=2))
