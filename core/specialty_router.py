#!/usr/bin/env python3
"""
core/specialty_router.py - Cerveau du routage médical

Ce module détermine la spécialité médicale requise en fonction des symptômes
et des signes vitaux du patient, selon 5 priorités ordonnées.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class Specialty(Enum):
    """Enum des spécialités médicales disponibles."""
    URGENCES = "Urgences"
    CARDIOLOGIE = "Cardiologie"
    NEUROLOGIE = "Neurologie"
    PNEUMOLOGIE = "Pneumologie"
    GENERALISTE = "Généraliste"


@dataclass
class VitalSigns:
    """Représentation des signes vitaux d'un patient."""
    fc: Optional[int] = None  # Fréquence cardiaque (bpm)
    ta_systolic: Optional[int] = None  # Tension artérielle systolique (mmHg)
    ta_diastolic: Optional[int] = None  # Tension artérielle diastolique (mmHg)
    spo2: Optional[int] = None  # Saturation en oxygène (%)
    temperature: Optional[float] = None  # Température (°C)
    fr: Optional[int] = None  # Fréquence respiratoire (rpm)
    consciousness: Optional[str] = None  # Niveau de conscience
    news2_score: Optional[int] = None  # Score NEWS2 (si déjà calculé)


def calculate_news2(vitals: VitalSigns) -> int:
    """
    Calcule le score NEWS2 (National Early Warning Score 2).
    
    Args:
        vitals: Signes vitaux du patient
        
    Returns:
        Score NEWS2 total (0-20)
    """
    score = 0
    
    # Fréquence respiratoire (FR)
    if vitals.fr is not None:
        if vitals.fr <= 8 or vitals.fr >= 25:
            score += 3
        elif 21 <= vitals.fr <= 24:
            score += 2
        elif 9 <= vitals.fr <= 11:
            score += 1
    
    # Saturation en oxygène (SpO2)
    if vitals.spo2 is not None:
        if vitals.spo2 <= 91:
            score += 3
        elif 92 <= vitals.spo2 <= 93:
            score += 2
        elif 94 <= vitals.spo2 <= 95:
            score += 1
    
    # Tension artérielle systolique
    if vitals.ta_systolic is not None:
        if vitals.ta_systolic <= 90:
            score += 3
        elif 91 <= vitals.ta_systolic <= 100:
            score += 2
        elif 101 <= vitals.ta_systolic <= 110:
            score += 1
    
    # Fréquence cardiaque (FC)
    if vitals.fc is not None:
        if vitals.fc <= 40 or vitals.fc >= 131:
            score += 3
        elif 111 <= vitals.fc <= 130:
            score += 2
        elif 41 <= vitals.fc <= 50 or 91 <= vitals.fc <= 110:
            score += 1
    
    # Niveau de conscience
    if vitals.consciousness:
        consciousness_lower = vitals.consciousness.lower()
        if consciousness_lower in ["confusion", "voix", "douleur", "inconscient", "altered"]:
            score += 3
    
    # Température
    if vitals.temperature is not None:
        if vitals.temperature <= 35.0 or vitals.temperature >= 39.1:
            score += 3
        elif 35.1 <= vitals.temperature <= 36.0 or 38.1 <= vitals.temperature <= 39.0:
            score += 1
    
    return score


def has_vital_symptom(symptoms: list) -> bool:
    """Vérifie si un symptôme vital critique est présent."""
    vital_symptoms = {
        "arrêt cardiaque", "cardiac_arrest", "respiratory_failure",
        "détresse respiratoire", "choc", "hypotension sévère",
        "hémorragie massive", "convulsions en cours", "coma"
    }
    
    symptoms_lower = {s.lower() for s in symptoms}
    return any(vs in symptoms_lower for vs in vital_symptoms)


def route(symptoms: list, vital_signs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Détermine la spécialité médicale requise selon les symptômes uniquement.
    
    Logique simplifiée sans NEWS2 ni signes vitaux:
    
    PRIORITÉ 1: Urgences (symptômes vitaux textuels)
    - Arrêt cardiaque, détresse respiratoire, choc, coma, etc.
    
    PRIORITÉ 2: Cardiologie
    - Douleur thoracique, palpitations
    
    PRIORITÉ 3: Neurologie
    - AVC, Convulsions, Traumatisme crânien, Perte de connaissance
    
    PRIORITÉ 4: Pneumologie
    - Essoufflement, toux sévère, difficulté respiratoire
    
    PRIORITÉ 5: Généraliste (Défaut)
    """
    # Normaliser les symptômes (minuscules, espaces → underscores)
    symptoms_lower = {s.lower().replace(" ", "_").replace("-", "_") for s in symptoms}
    
    # Ne pas utiliser les signes vitaux pour le routage
    # On garde le paramètre pour compatibilité mais on l'ignore
    routing_details = {
        "symptoms_checked": list(symptoms_lower),
        "method": "symptom_based_only"
    }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIORITÉ 1: URGENCES (Symptômes vitaux textuels uniquement)
    # ═══════════════════════════════════════════════════════════════════════════
    
    urgent_symptoms = {
        "arret_cardiaque", "cardiac_arrest", "arret_cardio_respiratoire",
        "detresse_respiratoire", "respiratory_distress", "detresse_respiratoire_aigue",
        "choc", "shock", "choc_hemorragique", "choc_cardiogenique",
        "coma", "etat_de_mal", "etat_de_choc", "agonie",
        "hemorragie_masive", "bleeding_severe", "perte_de_connaissance_severe",
        "etouffement", "suffocation", "asphyxie"
    }
    
    urgent_found = [s for s in symptoms_lower if any(u in s or s in u for u in urgent_symptoms)]
    if urgent_found:
        return {
            "specialty": Specialty.URGENCES.value,
            "priority": 1,
            "reason": f"Symptôme critique détecté: {', '.join(urgent_found)}",
            "routing_details": routing_details
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIORITÉ 2: CARDIOLOGIE (Mots-clés symptomatiques)
    # ═══════════════════════════════════════════════════════════════════════════
    
    cardio_symptoms = {
        "chest_pain", "douleur_thoracique", "douleur_toracique", "pain_chest",
        "thoracic_pain", "douleur_precordiale", "douleur_aigue_poitrine",
        "palpitations", "arythmie", "flutter", "tachycardie", "bradycardie"
    }
    
    cardio_found = [s for s in symptoms_lower if any(c in s or s in c for c in cardio_symptoms)]
    if cardio_found:
        return {
            "specialty": Specialty.CARDIOLOGIE.value,
            "priority": 2,
            "reason": f"Symptôme cardiaque: {', '.join(cardio_found)}",
            "routing_details": routing_details
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIORITÉ 3: NEUROLOGIE (Mots-clés symptomatiques)
    # ═══════════════════════════════════════════════════════════════════════════
    
    neuro_symptoms = {
        "stroke", "avc", "accident_vasculaire_cerebral", "ictus",
        "seizure", "convulsion", "convulsions", "crise_convulsive",
        "head_trauma", "traumatisme_cranien", "trauma_cranien", "tcc",
        "unconscious", "inconscient", "coma", "perte_connaissance",
        "paralysis", "paralysie", "hemiplegie", "tetraplegie", "paraplegie",
        "migraine_severe", "cephalee_violente", "douleur_tete_intense"
    }
    
    neuro_found = [s for s in symptoms_lower if any(n in s or s in n for n in neuro_symptoms)]
    if neuro_found:
        return {
            "specialty": Specialty.NEUROLOGIE.value,
            "priority": 3,
            "reason": f"Symptôme neurologique: {', '.join(neuro_found)}",
            "routing_details": routing_details
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIORITÉ 4: PNEUMOLOGIE (Mots-clés symptomatiques)
    # ═══════════════════════════════════════════════════════════════════════════
    
    pneumo_symptoms = {
        "shortness_of_breath", "essoufflement", "dyspnee", "dyspnée",
        "difficulte_respiratoire", "difficulté_respiratoire", "respiratory_difficulty",
        "toux_severe", "toux_importante", "toux_persistante",
        "wheezing", "sifflement", "sibilance",
        "respiratory_distress", "detresse_respiratoire_mineure"
    }
    
    pneumo_found = [s for s in symptoms_lower if any(p in s or s in p for p in pneumo_symptoms)]
    if pneumo_found:
        return {
            "specialty": Specialty.PNEUMOLOGIE.value,
            "priority": 4,
            "reason": f"Symptôme respiratoire: {', '.join(pneumo_found)}",
            "routing_details": routing_details
        }
    
    # ═══════════════════════════════════════════════════════════════════════════
    # PRIORITÉ 5: GÉNÉRALISTE (Défaut)
    # ═══════════════════════════════════════════════════════════════════════════
    
    return {
        "specialty": Specialty.GENERALISTE.value,
        "priority": 5,
        "reason": "Aucun critère de spécialisation détecté - cas général",
        "routing_details": routing_details
    }


def get_routing_summary(routing_result: Dict[str, Any]) -> str:
    """Génère un résumé textuel du routage."""
    return (
        f"[Routage] Spécialité: {routing_result['specialty']} "
        f"(Priorité {routing_result['priority']}) - {routing_result['reason']}"
    )
