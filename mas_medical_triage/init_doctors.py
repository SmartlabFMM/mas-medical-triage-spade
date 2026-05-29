"""
Script d'initialisation des médecins dans Google Sheets.
À exécuter après avoir réinitialisé la base de données.
"""

import uuid
from core.sheets_db import SheetsDB
from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME

# Médecins par défaut
DEFAULT_DOCTORS = [
    {
        "doctor_id": str(uuid.uuid4()),
        "nom": "Dr. Martin",
        "specialite": "Généraliste",
        "disponible": "TRUE",
        "patient_id": "",
        "charge": "0"
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "nom": "Dr. Bernard",
        "specialite": "Cardiologie",
        "disponible": "TRUE",
        "patient_id": "",
        "charge": "0"
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "nom": "Dr. Petit",
        "specialite": "Urgences",
        "disponible": "TRUE",
        "patient_id": "",
        "charge": "0"
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "nom": "Dr. Moreau",
        "specialite": "Neurologie",
        "disponible": "TRUE",
        "patient_id": "",
        "charge": "0"
    },
    {
        "doctor_id": str(uuid.uuid4()),
        "nom": "Dr. Roux",
        "specialite": "Pneumologie",
        "disponible": "TRUE",
        "patient_id": "",
        "charge": "0"
    }
]

def init_doctors():
    """Initialise les médecins par défaut."""
    print("🔧 Initialisation des médecins...")
    
    db = SheetsDB(
        credentials_path=GOOGLE_CREDENTIALS_PATH,
        spreadsheet_name=GOOGLE_SPREADSHEET_NAME
    )
    db.connect()
    
    # Vérifier si des médecins existent déjà
    existing = db.get_doctors()
    if existing:
        print(f"⚠️  {len(existing)} médecin(s) déjà existant(s)")
        response = input("Voulez-vous réinitialiser les médecins? (o/n): ")
        if response.lower() != 'o':
            print("❌ Opération annulée")
            return
        # Supprimer les médecins existants
        for doc in existing:
            db.delete_doctor(doc["doctor_id"])
    
    # Créer les médecins
    created = 0
    for doctor in DEFAULT_DOCTORS:
        try:
            # Ajouter directement à la feuille
            db._sheets["Doctors"].append_row(list(doctor.values()))
            print(f"  ✅ {doctor['nom']} ({doctor['specialite']})")
            created += 1
        except Exception as e:
            print(f"  ❌ Erreur: {doctor['nom']} - {e}")
    
    print(f"\n🎉 {created} médecin(s) créé(s) avec succès!")

if __name__ == "__main__":
    init_doctors()
