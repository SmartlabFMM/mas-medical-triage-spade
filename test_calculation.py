#!/usr/bin/env python3
"""Test de calcul avec âge 78 ans."""

import sys
sys.path.insert(0, 'c:/Users/MSI/Downloads/mas_medical_triage_spade/mas_medical_triage')

from utils.severity_calculator import compute_score, SYMPTOM_WEIGHTS

# Test avec patient 78 ans, les deux symptômes à intensité 3
symptoms = [
    {'name': 'Fièvre élevée', 'intensity': 3, 'duration': '4j'},
    {'name': 'Mal de tête', 'intensity': 3, 'duration': '4j'}
]

result = compute_score(symptoms, pain_level=5, age=78, is_conscious=True)

print("=== TEST AVEC ÂGE 78 ANS ===")
print(f"Symptômes: Fièvre élevée (intensité 3), Mal de tête (intensité 3)")
print(f"Âge: 78 ans (devrait activer multiplicateur 1.2)")
print(f"")
print(f"Score: {result['score']}")
print(f"Classification: {result['classification']}")
print(f"Multiplicateur: {result['multiplier']}")
print(f"")
print(f"Détails:")
for d in result.get('details', []):
    print(f"  - {d['normalized']}: poids={d['base_weight']}, intensité={d['intensity']}, facteur={d['intensity_factor']}, score={d['score']}")

print(f"")
print(f"Calcul attendu:")
print(f"  - Fièvre: 15 × 1.0 × 1.0 = 15")
print(f"  - Mal de tête: 20 × 1.0 × 1.0 = 20")
print(f"  - Sous-total: 35")
print(f"  - Multiplicateur âge (>70): 1.2")
print(f"  - TOTAL: 35 × 1.2 = 42")
