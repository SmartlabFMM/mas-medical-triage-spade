#!/usr/bin/env python3
"""Fix Google Sheets headers"""
import sys
sys.path.insert(0, '.')

from core.sheets_db import SheetsDB, HEADERS

db = SheetsDB()

# Get the Patients worksheet
ws = db._sheets['Patients']

# Get current headers
current_headers = ws.row_values(1)
print(f"Current headers: {current_headers}")
print(f"Expected headers: {HEADERS['Patients']}")

if len(current_headers) != len(HEADERS['Patients']):
    print(f"\n⚠️  Header mismatch! {len(current_headers)} vs {len(HEADERS['Patients'])}")
    print("Updating headers...")
    
    # Clear first row and add new headers
    # We need to insert a new column for symptoms_details
    # Insert column after "symptomes" (column E)
    ws.insert_cols([[]], 6)  # Insert empty column at position 6 (F)
    ws.update('F1', [['symptoms_details']])
    
    print("✅ Headers updated!")
else:
    print("\n✅ Headers are correct")
