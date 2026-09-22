"""Offline acceptance tests for the Chinese 4S sales demo."""

from __future__ import annotations

import json
from pathlib import Path

from domain import TestCRM, apply_approval, build_proposal, replay_decision

ROOT = Path(__file__).resolve().parent


def cases():
    return json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]


def test_case_set_covers_required_sales_shapes():
    categories = {item["category"] for item in cases()}
    assert {"高意向", "普通咨询", "竞品", "金融/价格异议", "投诉", "模糊/反讽"} <= categories
    assert len(cases()) >= 6


def test_positive_does_not_write_appointment_before_confirmation():
    case = next(item for item in cases() if item["id"] == "high_intent_i3")
    crm = TestCRM()
    decision = replay_decision(case, case["message"], "test-positive")
    proposal = build_proposal(decision, case, crm.snapshot())
    assert proposal["action"] == "await_customer_confirmation"
    assert crm.snapshot()["records"]["lead-zhang"]["appointment"] is None


def test_human_confirmation_writes_test_crm_and_is_idempotent():
    case = next(item for item in cases() if item["id"] == "high_intent_i3")
    crm = TestCRM()
    proposal = build_proposal(replay_decision(case, case["message"], "test-approval"), case, crm.snapshot())
    result = apply_approval(
        crm, proposal, customer_confirmed=True, idempotency_key="same", expected_epoch=proposal["epoch"], expected_revision=proposal["revision"]
    )
    assert result["status"] == "written"
    assert result["crm"]["records"]["lead-zhang"]["appointment"]["real_booking_system"] is False
    duplicate = apply_approval(
        crm, proposal, customer_confirmed=True, idempotency_key="same", expected_epoch=proposal["epoch"], expected_revision=proposal["revision"]
    )
    assert duplicate["status"] == "duplicate"
    assert len(duplicate["crm"]["records"]["lead-zhang"]["notes"]) == 1


def test_cancel_no_contact_blocks_even_if_human_tries_to_approve():
    case = next(item for item in cases() if item["id"] == "cancel_no_contact")
    crm = TestCRM()
    proposal = build_proposal(replay_decision(case, case["message"], "test-cancel"), case, crm.snapshot())
    result = apply_approval(
        crm, proposal, customer_confirmed=True, idempotency_key="cancel", expected_epoch=proposal["epoch"], expected_revision=proposal["revision"]
    )
    assert proposal["blocked_outreach"] is True
    assert result["status"] == "blocked"
    assert result["mutated"] is False


def test_stale_result_is_discarded_after_reset():
    case = next(item for item in cases() if item["id"] == "high_intent_i3")
    crm = TestCRM()
    proposal = build_proposal(replay_decision(case, case["message"], "test-stale"), case, crm.snapshot())
    crm.reset()
    result = apply_approval(
        crm, proposal, customer_confirmed=True, idempotency_key="stale", expected_epoch=proposal["epoch"], expected_revision=proposal["revision"]
    )
    assert result["status"] == "stale_discarded"
    assert result["mutated"] is False


def test_unknown_input_reclassifies_in_new_round():
    first = replay_decision(None, "临时陌生输入：只是问问，不确定是否买车。", "round-a")
    second = replay_decision(None, "取消并不要联系我。", "round-b")
    assert first["input_fingerprint"] != second["input_fingerprint"]
    assert first["answers"]["human_needed"]["noul"] >= 0.7
    assert second["answers"]["do_not_contact"]["noul"] >= 0.7


def test_workbench_exposes_truth_boundaries():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app.js").read_text(encoding="utf-8")
    for text in ("客户事实", "模型推断", "未知信息", "LIVE", "REPLAY", "测试 CRM", "未把客户意向自动写成预约"):
        assert text in html + js
    assert "input_fingerprint" in js
    assert "request_id" in js
    assert "latency_ms" in js
