#!/usr/bin/env python3
"""Debug Google Sheets patients"""
import sys
sys.path.insert(0, '.')

from core.sheets_db import SheetsDB

db = SheetsDB()
patients = db.get_patients()

print(f"Total patients: {len(patients)}")
for p in patients:
    pid = p.get('patient_id', 'N/A')
    statut = p.get('statut', 'N/A')
    score = p.get('score_gravité', p.get('score_gravite', 'N/A'))
    symptoms = p.get('symptomes', p.get('symptoms', 'N/A'))
    symptoms_details = p.get('symptoms_details', None)
    
    print(f"\nPatient: {pid}")
    print(f"  Statut: {statut}")
    print(f"  Score: {score}")
    print(f"  Symptoms: {symptoms}")
    print(f"  Symptoms Details: {symptoms_details}")
