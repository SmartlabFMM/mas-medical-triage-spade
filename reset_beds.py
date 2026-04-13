"""
reset_beds.py — Réinitialise les ressources du Sheet Google Sheets.
Lance ce script UNE FOIS pour remettre tous les lits en "disponible".

Usage :
    python reset_beds.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.sheets_db import SheetsDB
from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME
from datetime import datetime

db = SheetsDB(GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME)
db.connect()

ws = db._sheets["Resources"]
records = ws.get_all_records()
now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

reset_count = 0
for i, r in enumerate(records):
    row_idx = i + 2  # +2 car ligne 1 = headers
    ws.update(f"A{row_idx}:F{row_idx}", [[
        r.get("nom_ressource", f"Resource_{i}"),
        "True",   # disponibilite
        "0",      # charge_%
        "",       # patient_assigne
        "disponible",  # statut
        now,      # derniere_maj
    ]])
    reset_count += 1
    print(f"  ✓ {r.get('nom_ressource', '?')} → disponible")

print(f"\n{reset_count} ressources réinitialisées ✓")
