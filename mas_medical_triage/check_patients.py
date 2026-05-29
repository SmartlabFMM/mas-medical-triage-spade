#!/usr/bin/env python3
"""Check patients status"""
import sys
sys.path.insert(0, '.')

from core.sheets_db import SheetsDB

db = SheetsDB()
patients = db.get_patients()

print(f"\n{'='*60}")
print(f"Total patients: {len(patients)}")
print(f"{'='*60}")

for i, p in enumerate(patients[-5:]):  # Last 5 patients
    print(f"\nPatient {i+1}:")
    print(f"  ID: {p.get('patient_id')}")
    print(f"  Statut (statut): {repr(p.get('statut'))}")
    print(f"  Statut (status): {repr(p.get('status'))}")
    print(f"  Keys: {list(p.keys())}")
