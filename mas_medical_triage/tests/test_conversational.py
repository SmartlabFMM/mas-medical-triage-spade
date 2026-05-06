import pytest
from agents.conversational_agent import ConversationalAgent
from models.patient import Patient
from utils.helpers import uuid_gen

@pytest.fixture
def test_agent():
    return ConversationalAgent("test_conv@localhost", "pwd")

def test_conversational_agent_init(test_agent):
    assert str(test_agent.jid).startswith("test_conv")
