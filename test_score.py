#!/usr/bin/env python3
"""Test severity score calculation"""
import sys
sys.path.insert(0, '.')

from utils.severity_calculator import compute_score

# Test patient data (from your screenshot)
symptoms_details = [
    {"name": "Fièvre", "intensity": 3, "duration": "2h"},
    {"name": "Mal de tête", "intensity": 3, "duration": "2h"}
]

# Calcul avec 75 ans (multiplicateur 1.2)
result = compute_score(
    symptoms=symptoms_details,
    pain_level=8,
    age=75,
    is_conscious=True
)

print(f"Score calculé: {result['score']}")
print(f"Classification: {result['classification']}")
print(f"Multiplicateur: {result['multiplier']}")
print(f"\nDétails par symptôme:")
for d in result['details']:
    print(f"  - {d['name']}: base={d['base_weight']}, intensité={d['intensity']} (x{d['intensity_factor']:.2f}), durée={d['duration']} (x{d['duration_factor']:.2f}) = {d['score']}")

# Calcul attendu manuellement:
# Fièvre élevée (22) + Mal de tête (12) = 34
# Intensité 3 = x1.0, Durée 2h (persistante) = x1.2
# 34 * 1.0 * 1.2 = 40.8
# Âge 75 = x1.2 multiplicateur
# 40.8 * 1.2 = 48.96
print(f"\nScore attendu: ~48-51")
