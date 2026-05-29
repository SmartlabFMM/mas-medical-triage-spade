import pytest
from agents.meta_agent import MetaAgent

@pytest.fixture
def test_agent():
    return MetaAgent("test_meta@local", "pwd")

def test_meta_agent_init(test_agent):
    assert str(test_agent.jid).startswith("test_meta")
