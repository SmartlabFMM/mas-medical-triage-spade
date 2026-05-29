import pytest
from agents.resource_agent import ResourceAgent

@pytest.fixture
def test_agent():
    return ResourceAgent("test_res@local", "pwd")

def test_resource_agent_init(test_agent):
    assert str(test_agent.jid).startswith("test_res")
