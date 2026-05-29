import pytest
import asyncio
from agents.conversational_agent import ConversationalAgent
from agents.clinical_agent import ClinicalAgent
from agents.resource_agent import ResourceAgent
from agents.meta_agent import MetaAgent

@pytest.mark.asyncio
async def test_full_triage_cycle():
    """Test de création des agents."""
    conv = ConversationalAgent("test_conv@localhost", "pwd")
    clin = ClinicalAgent("test_clin@localhost", "pwd")
    res = ResourceAgent("test_res@localhost", "pwd")
    meta = MetaAgent("test_meta@localhost", "pwd")

    # On s'assure juste que les agents s'initialisent correctement
    assert str(conv.jid).startswith("test_conv")
    assert str(clin.jid).startswith("test_clin")
    assert str(res.jid).startswith("test_res")
    assert str(meta.jid).startswith("test_meta")
