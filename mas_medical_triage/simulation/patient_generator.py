"""
simulation/patient_generator.py — Générateur de patients simulés.
Utilise Faker pour produire des données réalistes. (ENF-TEST-02)
"""
from __future__ import annotations
import random
from faker import Faker
from models.patient import Patient
from utils.helpers import uuid_gen

fake = Faker("fr_FR")

SYMPTOM_POOLS = {
    "critique": ["arrêt cardiaque", "perte de conscience", "difficulté respiratoire", "avc"],
    "sévère":   ["douleur thoracique", "hémorragie", "fracture ouverte", "trauma crânien"],
    "modéré":   ["douleur abdominale", "fièvre élevée", "vomissements", "déshydratation"],
    "léger":    ["mal de tête", "toux", "nausée", "douleur musculaire"],
}


def generate_patient(severity: str = "random") -> Patient:
    """
    Génère un patient avec des symptômes cohérents selon la gravité.

    Args:
        severity: 'critique' | 'sévère' | 'modéré' | 'léger' | 'random'
    """
    if severity == "random":
        severity = random.choices(
            ["critique", "sévère", "modéré", "léger"],
            weights=[10, 20, 40, 30],
        )[0]

    pool = SYMPTOM_POOLS[severity]
    nb_symptoms = random.randint(1, min(3, len(pool)))
    symptoms = random.sample(pool, nb_symptoms)

    pain_map = {"critique": (7, 10), "sévère": (5, 8), "modéré": (3, 6), "léger": (0, 4)}
    pain = random.randint(*pain_map[severity])

    return Patient(
        id=uuid_gen(),
        name=fake.name(),
        age=random.randint(1, 95),
        gender=random.choice(["M", "F"]),
        symptoms=symptoms,
        pain_level=pain,
    )


def generate_batch(n: int = 5) -> list[Patient]:
    """Génère un lot de n patients avec gravités variées."""
    return [generate_patient() for _ in range(n)]
