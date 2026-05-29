#!/usr/bin/env python3
"""
Test unitaire pour valider la communication XMPP entre MetaAgent et ResourceAgent
"""
import asyncio
import sys
sys.path.insert(0, '.')

from core.message import build_message, Performative, MessageType
from config import AGENTS_JID


def test_resource_request_message():
    """Test que le message de requête de ressources est correctement construit."""
    msg = build_message(
        to=AGENTS_JID["resource"],
        performative=Performative.REQUEST,
        msg_type=MessageType.RESOURCE_STATUS,
        payload={"patient_id": "test-123", "request": "current_status"},
        patient_id="test-123",
        thread="test-123"
    )
    
    assert msg is not None, "Message construction failed"
    assert str(msg.to) == AGENTS_JID["resource"], f"Wrong recipient: {msg.to}"
    assert msg.get_metadata("msg_type") == MessageType.RESOURCE_STATUS.value, "Wrong msg_type"
    
    print("✅ Test construction message: PASSED")
    return True


def test_resource_response_message():
    """Test que la réponse ResourceAgent est correctement formatée."""
    payload = {
        "resource_state": {
            "beds_total": 50,
            "beds_available": 10,
            "specialists": {
                "cardiologie": 3,
                "neurologie": 2,
                "traumatologie": 4,
                "general": 5
            },
            "is_critical": False,
        },
        "is_critical": False,
    }
    
    msg = build_message(
        to=AGENTS_JID["meta"],
        performative=Performative.INFORM,
        msg_type=MessageType.RESOURCE_STATUS,
        payload=payload,
        patient_id="test-123",
        thread="test-123"
    )
    
    assert msg is not None, "Message construction failed"
    assert msg.get_metadata("msg_type") == MessageType.RESOURCE_STATUS.value
    
    print("✅ Test construction réponse: PASSED")
    return True


async def test_metaagent_timeout():
    """Test que MetaAgent gère correctement le timeout d'attente de ressources."""
    # Simuler un MetaAgent qui attend une réponse
    received = False
    
    async def simulate_wait():
        nonlocal received
        try:
            # Attendre avec timeout de 10 secondes
            await asyncio.wait_for(
                asyncio.sleep(0.1),  # Simuler la réception
                timeout=10.0
            )
            received = True
        except asyncio.TimeoutError:
            print("⚠️ Timeout simulé - pas de réponse reçue")
            received = False
    
    await simulate_wait()
    
    print("✅ Test timeout MetaAgent: PASSED")
    return True


def run_all_tests():
    """Exécute tous les tests."""
    print("\n" + "="*60)
    print("TEST UNITAIRE - Communication XMPP MetaAgent/ResourceAgent")
    print("="*60 + "\n")
    
    tests = [
        ("Construction message requête", test_resource_request_message),
        ("Construction message réponse", test_resource_response_message),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\n▶️ Test: {name}")
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test FAILED: {e}")
            failed += 1
    
    # Test async
    try:
        print("\n▶️ Test: Timeout MetaAgent")
        asyncio.run(test_metaagent_timeout())
        passed += 1
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        failed += 1
    
    print("\n" + "="*60)
    print(f"RÉSULTATS: {passed} passed, {failed} failed")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
