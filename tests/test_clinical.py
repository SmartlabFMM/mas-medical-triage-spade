import pytest
from agents.clinical_agent import ClinicalAgent
from utils.severity_calculator import compute_score

@pytest.fixture
def test_agent():
    return ClinicalAgent("test_clin@local", "pwd")

def test_clinical_agent_init(test_agent):
    assert str(test_agent.jid).startswith("test_clin")

def test_severity_score_critique():
    score = compute_score(["arrêt cardiaque"], pain_level=10, age=30)
    assert score == 100.0

def test_severity_score_faible():
    score = compute_score(["toux"], pain_level=1, age=30)
    assert score < 20.0
