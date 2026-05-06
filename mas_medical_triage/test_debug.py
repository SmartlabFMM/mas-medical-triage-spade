#!/usr/bin/env python3
"""Script de debug pour vérifier le calcul de gravité."""

import sys
sys.path.insert(0, 'c:/Users/MSI/Downloads/mas_medical_triage_spade/mas_medical_triage')

from utils.severity_calculator import compute_score, SYMPTOM_WEIGHTS, _normalize_symptom

# Vérifier les poids
print("=== POIDS DES SYMPTÔMES ===")
print(f'high_fever: {SYMPTOM_WEIGHTS.get("high_fever", "NOT FOUND")}')
print(f'fever: {SYMPTOM_WEIGHTS.get("fever", "NOT FOUND")}')
print(f'headache: {SYMPTOM_WEIGHTS.get("headache", "NOT FOUND")}')
print(f'mal de tête: {SYMPTOM_WEIGHTS.get("mal de tête", "NOT FOUND")}')
print(f'fièvre élevée: {SYMPTOM_WEIGHTS.get("fièvre élevée", "NOT FOUND")}')

# Test de normalisation
print("\n=== NORMALISATION ===")
print(f'Fièvre élevée -> {_normalize_symptom("Fièvre élevée")}')
print(f'Mal de tête -> {_normalize_symptom("Mal de tête")}')

# Test calcul
print("\n=== CALCUL ===")
symptoms = [
    {'name': 'Fièvre élevée', 'intensity': 2, 'duration': 'recente'},
    {'name': 'Mal de tête', 'intensity': 3, 'duration': 'recente'}
]

result = compute_score(symptoms, pain_level=0, age=22, is_conscious=True)
print(f'Score: {result["score"]}')
print(f'Classification: {result["classification"]}')
print(f'Détails: {result.get("details", [])}')
