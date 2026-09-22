"""Pure sales-demo policy, replay model, and test CRM state.

This module deliberately keeps business policy separate from Jev transport.
Run with ``python run_replay.py`` for the deterministic acceptance suite.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

AUTO_CONFIDENCE = 0.72
HUMAN_CONFIDENCE = 0.45
NOUL_YES = 0.70
CHOICE_FIELDS = ("intent", "lead_stage", "objection", "next_action")


def fingerprint(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def confidence(answer: dict[str, Any]) -> float:
    return float(answer.get("confidence", 0.0))


def min_choice_confidence(answers: dict[str, dict[str, Any]]) -> float:
    return min(confidence(answers.get(name, {})) for name in CHOICE_FIELDS)


def _answer_value(answers: dict[str, dict[str, Any]], name: str, key: str, default: Any = None) -> Any:
    return answers.get(name, {}).get(key, default)


def _dynamic_replay_answers(message: str) -> dict[str, dict[str, Any]]:
    text = message.lower()
    if any(token in message for token in ("不要再联系", "不要联系", "勿联系", "取消线索", "别打电话")):
        return {
            "intent": {"choice": "other", "confidence": 0.91},
            "lead_stage": {"choice": "consideration", "confidence": 0.78},
            "objection": {"choice": "none", "confidence": 0.88},
            "next_action": {"choice": "block_outreach", "confidence": 0.98},
            "high_value_lead": {"noul": 0.01},
            "human_needed": {"noul": 0.97},
            "do_not_contact": {"noul": 0.99},
            "appointment_confirmed": {"noul": 0.0},
        }
    if "周六" in message and any(token in message for token in ("先看看", "再说", "不确定", "别当我")):
        return {
            "intent": {"choice": "financing", "confidence": 0.46},
            "lead_stage": {"choice": "consideration", "confidence": 0.41},
            "objection": {"choice": "financing", "confidence": 0.45},
            "next_action": {"choice": "human_followup", "confidence": 0.38},
            "high_value_lead": {"noul": 0.28},
            "human_needed": {"noul": 0.86},
            "do_not_contact": {"noul": 0.02},
            "appointment_confirmed": {"noul": 0.04},
        }
    # An unknown replay input is intentionally conservative rather than a
    # lookup of the previous case.
    return {
        "intent": {"choice": "other", "confidence": 0.32},
        "lead_stage": {"choice": "awareness", "confidence": 0.30},
        "objection": {"choice": "none", "confidence": 0.28},
        "next_action": {"choice": "human_followup", "confidence": 0.31},
        "high_value_lead": {"noul": 0.18},
        "human_needed": {"noul": 0.88},
        "do_not_contact": {"noul": 0.01},
        "appointment_confirmed": {"noul": 0.0},
    }


def replay_decision(case: dict[str, Any] | None, message: str, round_id: str) -> dict[str, Any]:
    answers = deepcopy(case["replay_answers"]) if case and case.get("replay_answers") else _dynamic_replay_answers(message)
    case_id = case["id"] if case else "temporary_unknown"
    input_fingerprint = fingerprint({"case_id": case_id, "round_id": round_id, "message": message})
    return {
        "mode": "replay",
        "case_id": case_id,
        "round_id": round_id,
        "input_fingerprint": input_fingerprint,
        "model": "replay-fixture",
        "request_id": f"replay-{input_fingerprint}",
        "latency_ms": 0,
        "answers": answers,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def build_proposal(
    decision: dict[str, Any],
    case: dict[str, Any] | None,
    crm_snapshot: dict[str, Any],
) -> dict[str, Any]:
    answers = decision["answers"]
    facts = (case or {}).get("facts", {})
    do_not_contact = bool(facts.get("do_not_contact")) or _answer_value(answers, "do_not_contact", "noul", 0.0) >= NOUL_YES
    choice_min = min_choice_confidence(answers)
    model_human = _answer_value(answers, "human_needed", "noul", 0.0) >= NOUL_YES
    low_confidence = choice_min < HUMAN_CONFIDENCE
    next_action = _answer_value(answers, "next_action", "choice", "human_followup")
    appointment_confirmed = bool(facts.get("appointment_confirmed"))
    requires_human = model_human or low_confidence or next_action in {"book_test_drive", "human_followup", "finance_plan"}

    if do_not_contact:
        action = "block_outreach"
        band = "block"
        reason = "客户明确取消并要求勿联系；策略层禁止外呼，模型概率不能越权解除。"
        allowed_on_approval = False
    elif next_action == "book_test_drive" and not appointment_confirmed:
        action = "await_customer_confirmation"
        band = "human" if requires_human else "confirm"
        reason = "客户表达周六到店意向但未确认具体预约；不得把意向写成已预约。"
        allowed_on_approval = True
    elif requires_human:
        action = "human_review"
        band = "human"
        reason = "置信度或业务风险达到人工复核条件。"
        allowed_on_approval = True
    else:
        action = next_action
        band = "confirm" if choice_min < AUTO_CONFIDENCE else "auto"
        reason = "低风险建议仍需按确定性业务规则执行；本演示不自动写预约。"
        allowed_on_approval = False

    decision_id = fingerprint({"round_id": decision["round_id"], "input": decision["input_fingerprint"], "action": action})
    return {
        "decision_id": decision_id,
        "case_id": decision["case_id"],
        "round_id": decision["round_id"],
        "input_fingerprint": decision["input_fingerprint"],
        "epoch": crm_snapshot["epoch"],
        "revision": crm_snapshot["revision"],
        "action": action,
        "action_band": band,
        "reason": reason,
        "choice_min_confidence": choice_min,
        "human_needed": model_human,
        "requires_human_approval": requires_human,
        "allowed_on_explicit_human_approval": allowed_on_approval,
        "appointment_confirmed_by_customer": appointment_confirmed,
        "crm_mutation": False,
        "blocked_outreach": do_not_contact,
        "next_action": next_action,
    }


@dataclass
class TestCRM:
    """Small in-memory CRM. It is intentionally not a real appointment system."""

    epoch: str = field(default_factory=lambda: "epoch-" + uuid.uuid4().hex[:8])
    revision: int = 0
    records: dict[str, dict[str, Any]] = field(default_factory=dict)
    applied_idempotency: set[str] = field(default_factory=set)
    audit: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.records:
            self.records = {
                "lead-zhang": {
                    "id": "lead-zhang",
                    "name": "张先生",
                    "stage": "新线索",
                    "notes": [],
                    "followups": [],
                    "do_not_contact": False,
                    "appointment": None,
                }
            }

    def snapshot(self) -> dict[str, Any]:
        return {
            "epoch": self.epoch,
            "revision": self.revision,
            "records": deepcopy(self.records),
            "audit": deepcopy(self.audit),
        }

    def reset(self) -> dict[str, Any]:
        self.epoch = "epoch-" + uuid.uuid4().hex[:8]
        self.revision = 0
        self.applied_idempotency.clear()
        self.audit.clear()
        self.records = {}
        self.__post_init__()
        return self.snapshot()


# Pytest should not collect this implementation class as a test container.
TestCRM.__test__ = False


def apply_approval(
    crm: TestCRM,
    proposal: dict[str, Any],
    *,
    customer_confirmed: bool,
    idempotency_key: str,
    expected_epoch: str,
    expected_revision: int,
) -> dict[str, Any]:
    if idempotency_key in crm.applied_idempotency:
        return {"status": "duplicate", "mutated": False, "reason": "幂等键已处理", "crm": crm.snapshot()}
    if expected_epoch != crm.epoch or expected_revision != crm.revision or proposal.get("epoch") != crm.epoch:
        return {"status": "stale_discarded", "mutated": False, "reason": "结果已过时，未写入 CRM", "crm": crm.snapshot()}
    if proposal.get("blocked_outreach"):
        return {"status": "blocked", "mutated": False, "reason": "禁联策略阻止外呼和推进", "crm": crm.snapshot()}
    if not proposal.get("allowed_on_explicit_human_approval"):
        return {"status": "not_allowed", "mutated": False, "reason": "该动作没有可授权的 CRM 写入路径", "crm": crm.snapshot()}
    if not customer_confirmed:
        return {"status": "awaiting_customer_confirmation", "mutated": False, "reason": "未获得客户明确确认，保持待办", "crm": crm.snapshot()}

    record = crm.records["lead-zhang"]
    record["stage"] = "高意向"
    record["appointment"] = {
        "type": "试驾",
        "window": "周六下午",
        "status": "confirmed_by_human_in_test_crm",
        "real_booking_system": False,
    }
    record["notes"].append("人工确认：客户明确同意周六下午到店；仅写入测试 CRM")
    crm.applied_idempotency.add(idempotency_key)
    crm.revision += 1
    crm.audit.append({"event": "crm_write", "idempotency_key": idempotency_key, "revision": crm.revision})
    return {"status": "written", "mutated": True, "reason": "人工确认后写入测试 CRM", "crm": crm.snapshot()}


def visible_network_error(error: Exception) -> dict[str, Any]:
    return {
        "status": "network_error",
        "error_type": type(error).__name__,
        "message": "Live 请求失败；未降级为 Replay，未修改 CRM。",
        "no_mutation": True,
    }
