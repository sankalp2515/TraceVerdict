"""Case fixtures and isolation from developer-private credentials."""
from pathlib import Path
import pytest

from intentseal_core.decision_model import StaticDecisionModel
from intentseal_core.engine import Engine
from intentseal_core.policy import AgentPolicy, ToolPolicy
from intentseal_core.store import Store
from intentseal_gateway.cases.models import CreateCase
from intentseal_gateway.cases.service import CaseService


@pytest.fixture(autouse=True)
def isolate_developer_dotenv(monkeypatch):
    import intentseal_core.config as config
    original = config.dotenv_values
    private = (Path(__file__).resolve().parents[1] / ".env").resolve()

    def values(path, *args, **kwargs):
        if isinstance(path, (str, Path)) and Path(path).resolve() == private:
            return {}
        return original(path, *args, **kwargs)

    monkeypatch.setattr(config, "dotenv_values", values)


class CaseScorer:
    def score(self, text):
        return 0.0


@pytest.fixture
def tv_engine(tmp_path):
    policy = AgentPolicy(agent="research-agent", org="default", tools={"send_message": ToolPolicy()})
    e = Engine(policy_loader=lambda _: policy.model_copy(deep=True), store=Store(tmp_path / "cases.db"),
               decision_model=StaticDecisionModel(0), classifiers=[CaseScorer()])
    return e


@pytest.fixture
def tv_request():
    return CreateCase(agent_id="research-agent", fixture_id="supplier-contact", execution_mode="sample",
                      idempotency_key="sample-case-001")


@pytest.fixture
async def tv_service(tv_engine):
    service = CaseService(tv_engine)
    yield service
    await service.close()
