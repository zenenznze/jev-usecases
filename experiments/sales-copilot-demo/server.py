"""Serve the Chinese 4S sales workbench.

Replay works without credentials. Live mode reads TYPESAFE_API_KEY from the
server process only and exposes no credential material to the browser.
"""

from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from domain import TestCRM, apply_approval, build_proposal, replay_decision
from live_client import LiveAPIError, evaluate_live

ROOT = Path(__file__).resolve().parent


def load_cases() -> list[dict[str, Any]]:
    return json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))["cases"]


class DemoState:
    def __init__(self, default_mode: str) -> None:
        self.lock = threading.RLock()
        self.cases = load_cases()
        self.case_map = {case["id"]: case for case in self.cases}
        self.default_mode = default_mode
        self.mode = default_mode
        self.current_case_id = self.cases[0]["id"]
        self.current_message = self.case_map[self.current_case_id]["message"]
        self.crm = TestCRM()
        self.last_decision: dict[str, Any] | None = None
        self.last_proposal: dict[str, Any] | None = None
        self.proposals: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []

    def case(self, case_id: str | None) -> dict[str, Any] | None:
        return self.case_map.get(case_id or self.current_case_id)

    def public_cases(self) -> list[dict[str, Any]]:
        return [
            {
                "id": case["id"],
                "title": case["title"],
                "category": case["category"],
                "message": case["message"],
                "facts": case["facts"],
                "unknowns": case["unknowns"],
                "gold": case["gold"],
            }
            for case in self.cases
        ]

    def public_state(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "default_mode": self.default_mode,
            "current_case_id": self.current_case_id,
            "current_message": self.current_message,
            "last_decision": self.last_decision,
            "last_proposal": self.last_proposal,
            "crm": self.crm.snapshot(),
            "events": self.events[-30:],
        }

    def reset(self, case_id: str | None = None) -> dict[str, Any]:
        with self.lock:
            if case_id and case_id not in self.case_map:
                raise KeyError(case_id)
            self.current_case_id = case_id or self.cases[0]["id"]
            self.current_message = self.case_map[self.current_case_id]["message"]
            self.last_decision = None
            self.last_proposal = None
            self.proposals.clear()
            self.events.clear()
            self.crm.reset()
            self.events.append({"event": "reset", "case_id": self.current_case_id, "mode": self.mode})
            return self.public_state()

    def evaluate(self, mode: str, case_id: str | None, message: str, round_id: str) -> dict[str, Any]:
        with self.lock:
            if mode not in {"replay", "live"}:
                raise ValueError("mode must be replay or live")
            case = self.case(case_id)
            self.mode = mode
            self.current_case_id = case["id"] if case else "temporary_unknown"
            self.current_message = message
            try:
                decision = (
                    replay_decision(case, message, round_id)
                    if mode == "replay"
                    else evaluate_live(case, message, round_id)
                )
            except LiveAPIError as error:
                result = {
                    "status": "live_error",
                    "mode": "live",
                    "case_id": self.current_case_id,
                    "round_id": round_id,
                    "error_type": error.error_type,
                    "http_status": error.status,
                    "request_id": error.request_id or "unavailable",
                    "no_mutation": True,
                    "message": "Live 请求失败；没有降级为 Replay，也没有修改 CRM。",
                }
                self.events.append({"event": "live_error", **{key: result[key] for key in ("round_id", "error_type", "http_status")}})
                return result
            proposal = build_proposal(decision, case, self.crm.snapshot())
            self.last_decision = decision
            self.last_proposal = proposal
            self.proposals[proposal["decision_id"]] = proposal
            self.events.append(
                {
                    "event": "decision",
                    "mode": decision["mode"],
                    "round_id": decision["round_id"],
                    "input_fingerprint": decision["input_fingerprint"],
                    "model": decision["model"],
                    "request_id": decision["request_id"],
                    "latency_ms": decision["latency_ms"],
                    "action": proposal["action"],
                }
            )
            return {"status": "ok", "decision": decision, "proposal": proposal, "crm": self.crm.snapshot()}


class Handler(BaseHTTPRequestHandler):
    server: "DemoHTTPServer"

    def log_message(self, *_args: Any) -> None:
        return

    def _json(self, status: int, body: dict[str, Any]) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/cases":
            self._json(200, {"cases": self.server.demo.public_cases()})
            return
        if self.path == "/api/state":
            self._json(200, self.server.demo.public_state())
            return
        if self.path == "/api/crm":
            self._json(200, {"crm": self.server.demo.crm.snapshot()})
            return
        if self.path == "/api/health":
            self._json(200, {"status": "ok", "mode": self.server.demo.mode, "live_is_real": True})
            return
        if self.path == "/" or self.path == "/index.html":
            self._serve(ROOT / "index.html", "text/html; charset=utf-8")
            return
        if self.path == "/app.js":
            self._serve(ROOT / "app.js", "text/javascript; charset=utf-8")
            return
        self._json(404, {"error": "not_found"})

    def _serve(self, path: Path, content_type: str) -> None:
        if not path.is_file():
            self._json(404, {"error": "asset_not_found"})
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802
        try:
            body = self._body()
            if self.path == "/api/reset":
                self._json(200, self.server.demo.reset(body.get("case_id")))
                return
            if self.path == "/api/evaluate":
                round_id = str(body.get("round_id") or "round-1")
                message = str(body.get("message") or "")
                result = self.server.demo.evaluate(str(body.get("mode") or "replay"), body.get("case_id"), message, round_id)
                self._json(200 if result.get("status") != "live_error" else 502, result)
                return
            if self.path == "/api/approve":
                result = self.server.approve(body)
                self._json(200, result)
                return
            if self.path == "/api/reject":
                self.server.demo.events.append({"event": "human_rejected", "decision_id": body.get("decision_id")})
                self._json(200, {"status": "rejected", "mutated": False, "reason": "人工拒绝推进；CRM 未修改", "crm": self.server.demo.crm.snapshot()})
                return
            self._json(404, {"error": "not_found"})
        except KeyError as error:
            self._json(404, {"error": "unknown_case", "detail": str(error)})
        except (ValueError, json.JSONDecodeError) as error:
            self._json(400, {"error": "bad_request", "detail": str(error)})
        except Exception as error:  # noqa: BLE001
            self._json(500, {"error": type(error).__name__, "detail": "演示服务内部错误"})


class DemoHTTPServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], default_mode: str) -> None:
        super().__init__(address, Handler)
        self.demo = DemoState(default_mode)

    def approve(self, body: dict[str, Any]) -> dict[str, Any]:
        decision_id = str(body.get("decision_id") or "")
        proposal = self.demo.proposals.get(decision_id)
        if not proposal:
            return {"status": "missing_proposal", "mutated": False, "reason": "找不到当前轮次结果", "crm": self.demo.crm.snapshot()}
        result = apply_approval(
            self.demo.crm,
            proposal,
            customer_confirmed=bool(body.get("customer_confirmed")),
            idempotency_key=str(body.get("idempotency_key") or decision_id + "-approval"),
            expected_epoch=str(body.get("epoch") or ""),
            expected_revision=int(body.get("revision", -1)),
        )
        self.demo.events.append({"event": "approval", "decision_id": decision_id, "status": result["status"], "mutated": result["mutated"]})
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--mode", choices=("replay", "live"), default="replay")
    args = parser.parse_args()
    server = DemoHTTPServer((args.host, args.port), args.mode)
    print(f"sales-copilot-demo http://{args.host}:{args.port}/ mode={args.mode}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
