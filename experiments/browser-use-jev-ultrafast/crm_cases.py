"""Case labels, Jev result normalization, and CRM business policy.

This module owns no browser or credential state. Replay uses fixed labels;
live mode supplies the same decision shape from a real Jev response.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

CASES: dict[str, dict[str, Any]] = {
    "positive_high_value": {
        "label": "正向：高价值询价与试驾",
        "lead_id": "lead-zhang",
        "customer": "张先生",
        "message": "客户询价远航 X5，比较竞品，预算明确，周六下午希望试驾，价格合适近期购买。",
        "facts": [
            "客户明确询价",
            "客户给出车型与近期购买信号",
            "客户提出周六试驾时间",
        ],
        "unknowns": ["最终价格异议仍需销售确认"],
        "expected": {
            "priority": "high_value",
            "stage": "high_intent",
            "objection": "price",
            "next_action": "confirm_test_drive",
            "human_needed": True,
            "evidence_sufficient": True,
        },
    },
    "negative_refuse_contact": {
        "label": "反向：明确拒绝联系",
        "lead_id": "lead-li",
        "customer": "李女士",
        "message": "客户明确表示不要再联系，也不希望收到任何销售消息。",
        "facts": ["客户明确拒绝联系"],
        "unknowns": ["未来是否主动重新联系未知"],
        "expected": {
            "priority": "low_value",
            "stage": "hold",
            "objection": "none",
            "next_action": "no_contact",
            "human_needed": False,
            "evidence_sufficient": True,
        },
    },
    "challenge_insufficient_evidence": {
        "label": "现场挑战：陌生输入且证据不足",
        "lead_id": "lead-zhang",
        "customer": "张先生",
        "message": "再看看。",
        "facts": ["客户只留下短句，没有车型、预算、时间或购买意向"],
        "unknowns": ["购买意向未知", "是否愿意联系未知", "下一步时间未知"],
        "expected": {
            "priority": "unknown",
            "stage": "new_lead",
            "objection": "unknown",
            "next_action": "collect_evidence",
            "human_needed": True,
            "evidence_sufficient": False,
        },
    },
}

CHOICES = {
    "priority": {"high_value", "standard", "low_value", "unknown"},
    "stage": {"high_intent", "contacted", "hold", "new_lead"},
    "objection": {"price", "timing", "competition", "none", "unknown"},
    "next_action": {"confirm_test_drive", "send_info", "no_contact", "collect_evidence", "human_review"},
}


def replay_decision(case_id: str) -> dict[str, Any]:
    """Return the pre-labeled control decision without pretending it is live."""
    case = CASES[case_id]
    return {"source": "replay_label", "decision_id": f"replay:{case_id}", **deepcopy(case["expected"])}


def normalize_live_answers(answers: dict[str, Any], model: str | None) -> dict[str, Any]:
    """Validate the closed Jev answer shape before business policy consumes it."""
    result: dict[str, Any] = {
        "source": "live_jev",
        "model": model,
        "decision_id": "live:pending",
    }
    for key, allowed in CHOICES.items():
        answer = answers.get(key, {})
        choice = answer.get("choice")
        if choice not in allowed:
            raise ValueError(f"Invalid Jev {key} choice: {choice!r}")
        result[key] = choice
        if answer.get("confidence") is not None:
            result[f"{key}_confidence"] = float(answer["confidence"])
    for key in ("human_needed", "evidence_sufficient"):
        answer = answers.get(key, {})
        value = float(answer.get("noul"))
        if not 0 <= value <= 1:
            raise ValueError(f"Invalid Jev {key} probability")
        result[key] = value >= 0.5
        result[f"{key}_probability"] = value
    result["decision_id"] = "live:" + "-".join(
        str(result[key]) for key in ("priority", "stage", "objection", "next_action")
    )
    return result


def crm_policy(decision: dict[str, Any]) -> dict[str, Any]:
    """Translate Jev's judgment into an explicit, conservative CRM policy."""
    refusal = decision["next_action"] == "no_contact"
    sufficient = bool(decision["evidence_sufficient"])
    high_value = decision["priority"] == "high_value"
    allow_progress = high_value and sufficient and not refusal
    if refusal:
        reason = "客户明确拒绝联系：禁止推进阶段、备注触达或创建跟进。"
    elif not sufficient:
        reason = "证据不足：保持当前阶段，只允许补充证据，不允许高意向推进。"
    elif not high_value:
        reason = "当前 Jev 优先级不足：不允许高意向推进。"
    else:
        reason = "证据充分且为高价值线索；允许写入受控字段，跟进状态必须为待确认。"
    return {
        "allow_stage_high": allow_progress,
        "allow_note": allow_progress,
        "allow_pending_followup": allow_progress,
        "blocked_reason": None if allow_progress else reason,
        "human_review": bool(decision["human_needed"]),
        "contact_status": "blocked" if refusal else ("needs_evidence" if not sufficient else "allowed_pending_confirmation"),
    }


def case_payload(case_id: str, mode: str, decision: dict[str, Any]) -> dict[str, Any]:
    case = CASES[case_id]
    return {
        "case_id": case_id,
        "label": case["label"],
        "customer": case["customer"],
        "lead_id": case["lead_id"],
        "message": case["message"],
        "facts": case["facts"],
        "unknowns": case["unknowns"],
        "mode": mode,
        "decision": decision,
        "policy": crm_policy(decision),
    }
