import pytest

from app.ai import model_router


def test_route_reads_deployment_name_from_env(monkeypatch):
    monkeypatch.setenv("FOUNDRY_ADVISOR_DEPLOYMENT", "my-advisor")
    assert model_router.deployment_for("advise") == "my-advisor"


def test_unknown_task_raises():
    with pytest.raises(ValueError):
        model_router.deployment_for("translate")