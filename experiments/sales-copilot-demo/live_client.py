"""Real Jev/System One transport for the sales demo.

The client reads TYPESAFE_API_KEY only from the current process. It never
returns or logs that value. Each response is bound to a round and an input
fingerprint so Replay and Live evidence cannot be confused.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from domain import fingerprint

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
QUESTIONS: dict[str, dict[str, Any]] = {
    "intent": {
        "type": "choice",
        "instructions": "客户的主要购车意图",
        "criteria": {
            "price_inquiry": "询价",
            "comparison": "竞品比较",
            "financing": "分期金融",
            "test_drive": "预约试驾",
            "purchase": "近期购买",
            "other": "其他",
        },
    },
    "lead_stage": {
        "type": "choice",
        "instructions": "客户处于哪个销售阶段",
        "criteria": {
            "awareness": "初步了解",
            "consideration": "比较考虑",
            "evaluation": "具体评估",
            "ready": "准备推进下一步",
        },
    },
    "objection": {
        "type": "choice",
        "instructions": "客户当前主要异议",
        "criteria": {
            "price": "价格",
            "competition": "竞品",
            "financing": "分期压力",
            "product": "产品适配",
            "none": "无明确异议",
        },
    },
    "next_action": {
        "type": "choice",
        "instructions": "销售下一步最合适的动作",
        "criteria": {
            "quote": "提供核验报价",
            "compare": "提供竞品比较",
            "finance_plan": "核算金融方案",
            "book_test_drive": "确认试驾时段",
            "human_followup": "销售人工接管",
            "block_outreach": "阻止外呼和推进",
        },
    },
    "high_value_lead": {
        "type": "noul",
        "instructions": "客户有明确车型、购买时间和具体推进动作，属于高价值线索",
    },
    "human_needed": {
        "type": "noul",
        "instructions": "该客户需要销售人员人工接管，以处理报价、金融、投诉或试驾确认",
    },
    "do_not_contact": {
        "type": "noul",
        "instructions": "客户明确要求取消线索、退订或不要再联系",
    },
    "appointment_confirmed": {
        "type": "noul",
        "instructions": "客户已经明确确认了具体到店或试驾安排，而不是表达可能、考虑或有兴趣",
    },
}


class LiveAPIError(RuntimeError):
    def __init__(self, status: int | None, error_type: str, request_id: str | None = None) -> None:
        super().__init__(error_type)
        self.status = status
        self.error_type = error_type
        self.request_id = request_id


def _error_type(body: str) -> str:
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return "unparseable_response"
    detail = parsed.get("detail") if isinstance(parsed, dict) else None
    if isinstance(detail, dict) and detail.get("error_type"):
        return str(detail["error_type"])
    return "http_error"


def build_state(case: dict[str, Any] | None, message: str) -> dict[str, Any]:
    return {
        "case_id": (case or {}).get("id", "temporary_unknown"),
        "message": message,
        "known_customer_facts": (case or {}).get("facts", {}),
        "unknown_information": (case or {}).get("unknowns", []),
        "policy_note": "模型只做判断；策略层决定是否允许 CRM 写入或外呼。",
    }


def evaluate_live(case: dict[str, Any] | None, message: str, round_id: str) -> dict[str, Any]:
    api_key = os.getenv("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise LiveAPIError(None, "missing_typesafe_api_key")
    state = build_state(case, message)
    input_fingerprint = fingerprint({"round_id": round_id, "state": state})
    payload = {"state": state, "model": "jev-latest", "questions": QUESTIONS}
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8", "replace"))
            request_id = response.headers.get("x-typesafe-request-id")
            status = response.status
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", "replace")
        request_id = error.headers.get("x-typesafe-request-id") if error.headers else None
        raise LiveAPIError(error.code, _error_type(body), request_id) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise LiveAPIError(None, type(error).__name__) from None
    latency_ms = round((time.perf_counter() - started) * 1000, 1)
    return {
        "mode": "live",
        "case_id": (case or {}).get("id", "temporary_unknown"),
        "round_id": round_id,
        "input_fingerprint": input_fingerprint,
        "model": body.get("model"),
        "request_id": request_id or "unavailable",
        "latency_ms": latency_ms,
        "http_status": status,
        "answers": body.get("answers", {}),
        "usage": body.get("usage"),
    }
