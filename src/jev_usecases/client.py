"""Shared TypeSafe / Jev client bootstrap."""

from __future__ import annotations

from functools import lru_cache

from typesafe_sdk import TypeSafeClient


@lru_cache(maxsize=1)
def get_client(model: str | None = None) -> TypeSafeClient:
    """Return a cached TypeSafe client.

    The official SDK reads ``TYPESAFE_API_KEY`` from the process environment.
    An explicit ``model`` overrides the SDK default when supplied.
    """
    return TypeSafeClient(model=model)


def answers_to_dict(response) -> dict:
    """Normalize a System One response into plain JSON-serializable dicts."""
    out: dict = {
        "model": getattr(response, "model", None),
        "answers": {},
        "usage": None,
    }
    usage = getattr(response, "usage", None)
    if usage is not None:
        out["usage"] = {
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }

    answers = getattr(response, "answers", {}) or {}
    for key, ans in answers.items():
        kind = getattr(ans, "type", None) or type(ans).__name__.lower()
        entry: dict = {"type": kind}
        if hasattr(ans, "noul"):
            entry["noul"] = float(ans.noul)
        if hasattr(ans, "choice"):
            entry["choice"] = ans.choice
        if hasattr(ans, "probabilities") and ans.probabilities is not None:
            entry["probabilities"] = {str(k): float(v) for k, v in dict(ans.probabilities).items()}
        if hasattr(ans, "score"):
            entry["score"] = float(ans.score)
        if hasattr(ans, "confidence") and ans.confidence is not None:
            entry["confidence"] = float(ans.confidence)
        if hasattr(ans, "legend") and ans.legend is not None:
            entry["legend"] = {str(k): v for k, v in dict(ans.legend).items()}
        out["answers"][key] = entry
    return out
