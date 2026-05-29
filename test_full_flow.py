#!/usr/bin/env python3
"""Test du flux complet API → Agents"""
import sys
sys.path.insert(0, '.')

import urllib.request
import json

# Test 1: Appel direct à l'API
print("=== TEST 1: Appel direct API ===")
url = "http://127.0.0.1:5000/symptoms"
data = {
    "age": 78,
    "gender": "M",
    "symptoms": ["fievre_elevee", "mal_de_tete"],
    "pain_level": 5,
    "conscious": True,
    "symptoms_details": [
        {"name": "Fièvre élevée", "intensity": 3, "duration": "4j"},
        {"name": "Mal de tête", "intensity": 3, "duration": "4j"}
    ]
}

try:
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode(), 
        headers={'Content-Type': 'application/json'}, 
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode())
        print(f"Score API: {result.get('severity_score')}")
        print(f"Decision: {result.get('decision')}")
        print(f"Explanation: {result.get('explanation')}")
except Exception as e:
    print(f"Erreur API: {e}")

# Test 2: Calculateur direct
print("\n=== TEST 2: Calculateur direct ===")
from utils.severity_calculator import compute_score

symptoms = [
    {'name': 'Fièvre élevée', 'intensity': 3, 'duration': '4j'},
    {'name': 'Mal de tête', 'intensity': 3, 'duration': '4j'}
]

result = compute_score(symptoms, pain_level=5, age=78, is_conscious=True)
print(f"Score: {result['score']}")
print(f"Classification: {result['classification']}")
print(f"Multiplier: {result['multiplier']}")

print("\n=== CALCUL ATTENDU ===")
print("Fièvre: 15 × 1.0 (intensité 3) × 1.2 (durée 4j) = 18")
print("Mal de tête: 20 × 1.0 (intensité 3) × 1.2 (durée 4j) = 24")
print("Sous-total: 42")
print("Multiplicateur âge 78: 1.2")
print("TOTAL: 42 × 1.2 = 50.4")
