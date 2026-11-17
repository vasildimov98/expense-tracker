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


def test_ask_refuses_before_calling_the_model_when_cap_is_spent(monkeypatch):
    from app.ai import usage

    def spent():
        raise usage.DailyCapExceeded("cap")

    called = []
    monkeypatch.setattr(usage, "check_cap", spent)
    monkeypatch.setattr(model_router, "_client", lambda: called.append(1))
    with pytest.raises(usage.DailyCapExceeded):
        model_router.ask("categorize", "i", "x", 20)
    assert called == []      # no client was even built: nothing was spent


def test_ask_safe_turns_a_filter_block_into_a_result_without_retrying(monkeypatch):
    import httpx2 as httpx
    import openai
    from app.ai.safety import Outcome

    monkeypatch.setenv("FOUNDRY_MODEL_DEPLOYMENT", "primary")
    monkeypatch.delenv("FOUNDRY_FALLBACK_CATEGORIZE", raising=False)
    calls = []

    class FakeResponses:
        def create(self, model, **kwargs):
            calls.append(model)
            response = httpx.Response(400, request=httpx.Request("POST", "https://example.test"))
            raise openai.BadRequestError("x", response=response, body={"code": "content_filter"})

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(model_router, "_client", lambda: FakeClient())
    result = model_router.ask_safe("categorize", "i", "x", 20)
    assert result.outcome is Outcome.PROMPT_BLOCKED
    assert calls == ["primary"]      # a blocked prompt is not retried
