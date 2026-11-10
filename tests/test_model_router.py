import pytest

from app.ai import model_router


def test_route_reads_deployment_name_from_env(monkeypatch):
    monkeypatch.setenv("FOUNDRY_ADVISOR_DEPLOYMENT", "my-advisor")
    assert model_router.deployment_for("advise") == "my-advisor"


def test_unknown_task_raises():
    with pytest.raises(ValueError):
        model_router.deployment_for("translate")

def test_fallbacks_parse_comma_separated_names(monkeypatch):
    monkeypatch.setenv("FOUNDRY_FALLBACK_CATEGORIZE", " a , b ,,")
    assert model_router.fallbacks_for("categorize") == ["a", "b"]


def test_fallbacks_empty_when_unset(monkeypatch):
    monkeypatch.delenv("FOUNDRY_FALLBACK_ADVISE", raising=False)
    assert model_router.fallbacks_for("advise") == []


def test_ask_retries_then_fails_over(monkeypatch):
    """ask() must go through call_with_retry: primary throttled -> fallback answers."""
    from tests.test_resilience import make_429

    monkeypatch.setenv("FOUNDRY_MODEL_DEPLOYMENT", "primary")
    monkeypatch.setenv("FOUNDRY_FALLBACK_CATEGORIZE", "fallback")
    monkeypatch.setattr("app.ai.resilience.time.sleep", lambda s: None)  # no real waiting
    seen = []

    class FakeResponses:
        def create(self, model, **kwargs):
            seen.append(model)
            if model == "primary":
                raise make_429()
            return type("R", (), {"output_text": f"from {model}"})()

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(model_router, "_client", lambda: FakeClient())
    assert model_router.ask("categorize", "i", "x", 20) == "from fallback"
    assert seen[-1] == "fallback" and seen[0] == "primary"
