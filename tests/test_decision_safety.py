"""Safety-decision regressions with mocked model responses. No network."""

from types import SimpleNamespace

import pytest

from jev_usecases.decisions import Thresholds
from jev_usecases.models import UseCaseResult
from jev_usecases.soc import agents
from jev_usecases.use_cases import coding_agent_guardrails as tool_gate
from jev_usecases.use_cases import security_copilot
from jev_usecases.use_cases.security_incidents import SecurityAlert


SAFETY_KEYS = (
    "intent_coverage",
    "no_secret_egress",
    "no_irreversible_damage",
    "local_scope",
    "path_not_protected",
    "no_fetched_code_execution",
    "prompt_injection_absent",
    "policy_compliance",
)


def _stub_answers(monkeypatch: pytest.MonkeyPatch, module, answers: dict):
    raw = {"answers": answers, "model": "test-model", "usage": {}}
    client = SimpleNamespace(system_one=lambda **kwargs: raw)
    monkeypatch.setattr(module, "get_client", lambda: client)
    monkeypatch.setattr(module, "answers_to_dict", lambda response: response)


def _tool_answers() -> dict:
    answers = {key: {"noul": 0.99} for key in SAFETY_KEYS}
    answers["risk_class"] = {"choice": "read_only", "confidence": 0.99}
    answers["severity"] = {"score": 0.0}
    return answers


def _tool_request() -> tool_gate.ToolCallGate:
    return tool_gate.ToolCallGate(
        tool_name="bash", command_or_args="pwd", user_goal="Show the working directory"
    )


@pytest.mark.parametrize("safety_key", SAFETY_KEYS)
@pytest.mark.parametrize(
    ("probability", "expected"),
    [
        (0.0, "block"), (0.15, "block"), (0.1501, "ask"), (0.20, "ask"),
        (0.30, "ask"), (0.7499, "ask"), (0.75, "allow"), (1.0, "allow"),
    ],
)
def test_tool_gate_threshold_boundaries_for_each_safety_condition(monkeypatch, safety_key, probability, expected):
    answers = _tool_answers()
    answers[safety_key] = {"noul": probability}
    _stub_answers(monkeypatch, tool_gate, answers)

    result = tool_gate.gate_tool_call(_tool_request())

    assert result.decision == expected
    assert result.action_band == {"block": "block", "ask": "confirm", "allow": "auto"}[expected]


def test_tool_gate_respects_a_custom_affirmative_floor(monkeypatch):
    answers = _tool_answers()
    answers["no_secret_egress"] = {"noul": 0.8}
    _stub_answers(monkeypatch, tool_gate, answers)

    result = tool_gate.gate_tool_call(_tool_request(), thresholds=Thresholds(noul_yes=0.9))

    assert result.decision == "ask"


@pytest.mark.parametrize("inbound", ["block", "review", "allow"])
@pytest.mark.parametrize("outbound", ["block", "review", "allow"])
def test_guarded_answer_only_calls_llm_after_explicit_allow(monkeypatch, inbound, outbound):
    checks = []
    completions = []

    def evaluate(*args, **kwargs):
        decision = inbound if not checks else outbound
        checks.append(decision)
        return UseCaseResult(
            use_case="llm_guardrails", decision=decision,
            action_band={"allow": "auto", "review": "confirm", "block": "block"}[decision],
            rationale="Mocked guardrail decision", raw_answers={"decision": decision},
            model="test-model", usage={"input_tokens": 1},
        )

    def complete(*args, **kwargs):
        completions.append(True)
        return SimpleNamespace(
            provider="test", model="test-model", text="A synthetic answer", usage={}, key_env="NONE"
        )

    monkeypatch.setattr(security_copilot, "evaluate_guardrail", evaluate)
    monkeypatch.setattr(security_copilot, "complete", complete)
    result = security_copilot.run_guarded_security_answer(
        security_copilot.GuardedSecurityQuestion(question="A synthetic defensive question")
    )

    if inbound != "allow":
        assert checks == [inbound]
        assert completions == []
        assert result.metadata == {"llm_called": False, "answer": None}
        assert result.raw_answers == {"inbound": {"decision": inbound}}
        assert result.model == "test-model"
        assert result.usage == {"input_tokens": 1}
        assert result.decision == {"block": "blocked_prompt", "review": "prompt_needs_review"}[inbound]
        assert result.action_band == {"block": "block", "review": "confirm"}[inbound]
        assert "return_answer" not in result.actions
    else:
        assert checks == [inbound, outbound]
        assert completions == [True]
        assert result.metadata["llm_called"] is True
        assert result.decision == {
            "block": "blocked_completion", "review": "answered_needs_review", "allow": "answered"
        }[outbound]
        assert ("return_answer" in result.actions) is (outbound == "allow")


def _alert() -> SecurityAlert:
    return SecurityAlert(
        alert_name="Synthetic alert", description="Offline test fixture",
        host="test-host", environment="test",
    )


@pytest.mark.parametrize(
    ("choice", "expected", "action", "band"),
    [
        ("remain_isolated", "remain_isolated", "keep:isolation", "confirm"),
        ("human_review", "remain_isolated", "handoff:recovery", "human"),
        ("limited_restore", "limited_restore", "restore:limited", "confirm"),
        ("full_restore", "full_restore", "restore:full", "confirm"),
    ],
)
def test_recovery_respects_high_confidence_choices(monkeypatch, choice, expected, action, band):
    _stub_answers(monkeypatch, agents, {
        "safe_to_restore": {"noul": 0.99}, "residual_risk": {"score": 0.0},
        "restore_choice": {"choice": choice, "confidence": 0.99},
    })
    result = agents.run_recovery_agent(agents.RecoveryRequest(
        alert=_alert(), triage_decision="contain_now", containment_actions_completed=["isolate_host"],
        monitoring_clean=True, hours_contained=8,
    ))

    assert result.decision == expected
    assert result.action_band == band
    assert action in result.actions
    if choice != "full_restore":
        assert "restore:full" not in result.actions


@pytest.mark.parametrize(
    ("choice", "expected", "action"),
    [
        ("monitor", "monitor", "monitor:open_case"),
        ("reopen", "reopen", "reopen:investigation"),
        ("close", "close", "close:case"),
    ],
)
def test_closeout_respects_high_confidence_choices(monkeypatch, choice, expected, action):
    _stub_answers(monkeypatch, agents, {
        "notes_complete": {"noul": 0.99}, "recurrence_risk": {"score": 0.0},
        "close_choice": {"choice": choice, "confidence": 0.99},
    })
    result = agents.run_closeout_agent(agents.CloseoutRequest(
        alert=_alert(), triage_decision="contain_now", recovery_decision="full_restore", monitoring_clean=True,
    ))

    assert result.decision == expected
    assert result.action_band == "confirm"
    assert result.actions == [action]
