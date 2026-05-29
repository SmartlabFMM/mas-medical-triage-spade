#!/usr/bin/env python3
"""
reset_doctors.py - Script d'initialisation de la base des médecins

Ce script crée ou réinitialise l'onglet "Doctors" dans Google Sheets
et le peuple avec 8 médecins fictifs répartis dans les différentes spécialités.

Usage:
    python reset_doctors.py

Note:
    Ce script doit être exécuté une seule fois pour initialiser la base.
    Il supprimera l'onglet existant s'il existe déjà.
"""

import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime


def reset_doctors_sheet():
    """
    Crée ou réinitialise l'onglet Doctors avec 8 médecins fictifs.
    """
    print("=" * 70)
    print("  Réinitialisation de la base des médecins")
    print("=" * 70)
    
    # Importer SheetsDB et config
    try:
        from core.sheets_db import SheetsDB
        from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME
        db = SheetsDB(credentials_path=GOOGLE_CREDENTIALS_PATH, spreadsheet_name=GOOGLE_SPREADSHEET_NAME)
        db.connect()  # Connexion explicite requise
        print("[OK] Connexion à Google Sheets établie")
    except Exception as e:
        print(f"[ERREUR] Impossible de se connecter à Google Sheets: {e}")
        return False
    
    # Supprimer l'onglet existant s'il existe
    try:
        if "Doctors" in db._sheets:
            worksheet = db._sheets["Doctors"]
            db._spreadsheet.del_worksheet(worksheet)
            print("[OK] Ancien onglet Doctors supprimé")
    except Exception as e:
        print(f"[INFO] Pas d'onglet existant à supprimer: {e}")
    
    # Créer le nouvel onglet
    try:
        from core.sheets_db import HEADERS
        ws = db._spreadsheet.add_worksheet(
            title="Doctors",
            rows=100,
            cols=len(HEADERS["Doctors"])
        )
        ws.append_row(HEADERS["Doctors"])
        db._sheets["Doctors"] = ws
        print("[OK] Nouvel onglet Doctors créé")
    except Exception as e:
        print(f"[ERREUR] Impossible de créer l'onglet Doctors: {e}")
        return False
    
    # Définition des 8 médecins fictifs
    doctors = [
        # Urgences (2 médecins)
        {
            "doctor_id": "URG001",
            "nom": "Dr. Martin Dubois",
            "specialite": "Urgences",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "doctor_id": "URG002",
            "nom": "Dr. Sophie Laurent",
            "specialite": "Urgences",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        
        # Cardiologie (2 médecins)
        {
            "doctor_id": "CAR001",
            "nom": "Dr. Pierre Moreau",
            "specialite": "Cardiologie",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "doctor_id": "CAR002",
            "nom": "Dr. Isabelle Bernard",
            "specialite": "Cardiologie",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        
        # Neurologie (1 médecin)
        {
            "doctor_id": "NEU001",
            "nom": "Dr. Jean-Luc Petit",
            "specialite": "Neurologie",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        
        # Pneumologie (1 médecin)
        {
            "doctor_id": "PNE001",
            "nom": "Dr. Catherine Roux",
            "specialite": "Pneumologie",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        
        # Généraliste (2 médecins)
        {
            "doctor_id": "GEN001",
            "nom": "Dr. Philippe Durand",
            "specialite": "Généraliste",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        {
            "doctor_id": "GEN002",
            "nom": "Dr. Marie Lefebvre",
            "specialite": "Généraliste",
            "disponible": "TRUE",
            "patient_assigne": "",
            "derniere_maj": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    ]
    
    # Ajouter les médecins à la feuille
    try:
        for doctor in doctors:
            row = [
                doctor["doctor_id"],
                doctor["nom"],
                doctor["specialite"],
                doctor["disponible"],
                doctor["patient_assigne"],
                doctor["derniere_maj"]
            ]
            ws.append_row(row)
        
        print(f"[OK] {len(doctors)} médecins ajoutés avec succès")
    except Exception as e:
        print(f"[ERREUR] Impossible d'ajouter les médecins: {e}")
        return False
    
    # Afficher le résumé
    print("\n" + "=" * 70)
    print("  Résumé de la base des médecins")
    print("=" * 70)
    
    specialty_count = {}
    for doctor in doctors:
        spec = doctor["specialite"]
        specialty_count[spec] = specialty_count.get(spec, 0) + 1
    
    for specialty, count in specialty_count.items():
        print(f"  • {specialty}: {count} médecin(s)")
    
    print(f"\n  TOTAL: {len(doctors)} médecins créés")
    print("=" * 70)
    print("\n[OK] Initialisation terminée avec succès!")
    print("La base des médecins est prête à être utilisée.")
    
    return True


if __name__ == "__main__":
    success = reset_doctors_sheet()
    sys.exit(0 if success else 1)
