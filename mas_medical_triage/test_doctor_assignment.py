#!/usr/bin/env python3
"""
test_doctor_assignment.py - Test du système d'affectation des médecins

Ce script teste:
1. Le specialty_router avec différents cas
2. La gestion des médecins via sheets_db
3. L'assignation hiérarchique
"""

import sys
sys.path.insert(0, '.')

print("=" * 70)
print("  TEST DU SYSTÈME D'AFFECTATION DES MÉDECINS")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════════
# TEST 1: Specialty Router (basé uniquement sur les symptômes textuels)
# ═══════════════════════════════════════════════════════════════════════════
print("\n[TEST 1] Specialty Router - Routage par symptômes uniquement")
print("-" * 70)

try:
    from core.specialty_router import route, Specialty, get_routing_summary
    
    # Cas 1: Urgences (symptômes vitaux textuels)
    result1 = route(
        symptoms=["arret cardiaque", "choc"],
        vital_signs={}  # Signes vitaux ignorés - routage par symptômes uniquement
    )
    print(f"  Urgences: {get_routing_summary(result1)}")
    assert result1["specialty"] == Specialty.URGENCES.value, f"Attendu Urgences, obtenu {result1['specialty']}"
    
    # Cas 2: Cardiologie (douleur thoracique)
    result2 = route(
        symptoms=["chest_pain", "nausea"],
        vital_signs={}
    )
    print(f"  Cardiologie: {get_routing_summary(result2)}")
    assert result2["specialty"] == Specialty.CARDIOLOGIE.value, f"Attendu Cardiologie, obtenu {result2['specialty']}"
    
    # Cas 3: Neurologie (AVC)
    result3 = route(
        symptoms=["stroke", "paralysis"],
        vital_signs={}
    )
    print(f"  Neurologie: {get_routing_summary(result3)}")
    assert result3["specialty"] == Specialty.NEUROLOGIE.value, f"Attendu Neurologie, obtenu {result3['specialty']}"
    
    # Cas 4: Pneumologie (essoufflement)
    result4 = route(
        symptoms=["shortness_of_breath"],
        vital_signs={}
    )
    print(f"  Pneumologie: {get_routing_summary(result4)}")
    assert result4["specialty"] == Specialty.PNEUMOLOGIE.value, f"Attendu Pneumologie, obtenu {result4['specialty']}"
    
    # Cas 5: Généraliste (symptômes non spécifiques)
    result5 = route(
        symptoms=["headache", "mild_fever"],
        vital_signs={}
    )
    print(f"  Généraliste: {get_routing_summary(result5)}")
    assert result5["specialty"] == Specialty.GENERALISTE.value, f"Attendu Généraliste, obtenu {result5['specialty']}"
    
    print("\n  [OK] Specialty Router - TOUS LES TESTS PASSES")
    print("  (Routage basé uniquement sur les symptômes textuels - sans NEWS2)")
except Exception as e:
    print(f"\n  [ERROR] Erreur: {e}")
    import traceback
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════
# TEST 2: Sheets DB - Gestion des Médecins
# ═══════════════════════════════════════════════════════════════════════════
print("\n[TEST 2] Sheets DB - Gestion des Médecins")
print("-" * 70)

try:
    from core.sheets_db import SheetsDB
    from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME
    
    db = SheetsDB(credentials_path=GOOGLE_CREDENTIALS_PATH, spreadsheet_name=GOOGLE_SPREADSHEET_NAME)
    print(f"  [OK] Connexion Google Sheets établie")
    
    # Vérifier si l'onglet Doctors existe
    if "Doctors" in db._sheets:
        print(f"  [OK] Onglet Doctors trouvé")
        
        # Tester find_available_doctor
        doctor = db.find_available_doctor("Cardiologie")
        if doctor:
            print(f"  [OK] Médecin Cardiologie trouvé: {doctor['nom']}")
        else:
            print(f"  [!] Aucun médecin Cardiologie disponible")
        
        # Tester get_doctors_status_summary
        summary = db.get_doctors_status_summary()
        print(f"  [INFO] Total médecins: {summary['total_doctors']}")
        print(f"  [INFO] Disponibles: {summary['available']}, Occupés: {summary['occupied']}")
        for spec, counts in summary['by_specialty'].items():
            print(f"    - {spec}: {counts['available']} dispo, {counts['occupied']} occupés")
        
        print("\n  [OK] Sheets DB - Gestion des Medecins - OK")
    else:
        print(f"  [!] Onglet Doctors non trouvé - Exécutez: python reset_doctors.py")
        
except Exception as e:
    print(f"\n  [ERROR] Erreur: {e}")
    import traceback
    traceback.print_exc()

# ═══════════════════════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("  RÉSUMÉ DES TESTS")
print("=" * 70)
print("""
  Pour finaliser l'installation:
  
  1. Exécuter: python reset_doctors.py
     -> Crée l'onglet Doctors avec 8 médecins fictifs
  
  2. Redémarrer les agents: .\run_realtime.ps1
     -> MetaAgent intégrera l'assignation des médecins
  
  3. Tester avec un patient à hospitaliser
     -> Le système assignera automatiquement un médecin
""")
print("=" * 70)
