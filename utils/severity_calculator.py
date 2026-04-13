"""
utils/severity_calculator.py — Calcul du score de gravité médicale.
Partagé entre agents sans duplication (SOLID). (EF-CLI-01)
Score de 0 (faible) à 100 (critique).
"""
from __future__ import annotations
import unicodedata

# Règles métier : symptôme → points de gravité
SYMPTOM_WEIGHTS: dict[str, float] = {
    # Critique
    "douleur thoracique":        45.0,
    "arrêt cardiaque":           100.0,
    "perte de conscience":       50.0,
    "difficulté respiratoire":   40.0,
    "avc":                       55.0,
    "convulsions":               45.0,
    "hémorragie":                50.0,
    # Sévère
    "fracture ouverte":          35.0,
    "brûlure grave":             35.0,
    "trauma crânien":            40.0,
    "hypoglycémie":              30.0,
    # Modéré
    "fièvre élevée":             20.0,
    "douleur abdominale":        25.0,
    "vomissements":              15.0,
    "déshydratation":            20.0,
    # Léger
    "mal de tête":               10.0,
    "toux":                       5.0,
    "douleur musculaire":         8.0,
    "nausée":                    10.0,
    "douleur_main":              12.0,  # Pain in hand
    "douleur_articulaire":       15.0,  # Joint pain
    # Canonical EN tokens from chat/API extraction
    "chest_pain":                45.0,
    "shortness_of_breath":       40.0,
    "loss_of_consciousness":     50.0,
    "high_fever":                20.0,
    "fever":                     12.0,
    "headache":                  10.0,
    "nausea":                    10.0,
    "vomiting":                  15.0,
    "dizziness":                 12.0,
    "bleeding":                  50.0,
    "stroke":                    55.0,
    "confusion":                 28.0,
    "trauma":                    35.0,
    "pain_in_hand":              12.0,  # Normalized "pain in hand"
    "hand_pain":                 12.0,
    "joint_pain":                15.0,
    "muscle_pain":               8.0,
    "back_pain":                 18.0,
    "stomach_pain":              25.0,
}

PAIN_WEIGHT: float = 3.0     # points par niveau de douleur (0-10)
AGE_THRESHOLD_HIGH: int = 70  # > 70 ans → +10 points
AGE_THRESHOLD_LOW: int  = 5   # < 5 ans  → +10 points

SYMPTOM_ALIASES: dict[str, str] = {
    # FR -> canonical
    "douleur_thoracique": "chest_pain",
    "difficulte_respiratoire": "shortness_of_breath",
    "difficultes_respiratoires": "shortness_of_breath",
    "essoufflement": "shortness_of_breath",
    "perte_de_conscience": "loss_of_consciousness",
    "fievre_elevee": "high_fever",
    "fievre": "fever",
    "mal_de_tete": "headache",
    "nausee": "nausea",
    "vomissements": "vomiting",
    "hemorragie": "bleeding",
    "trauma_cranien": "trauma",
    "vertiges": "dizziness",
    "avc": "stroke",
    "douleur_main": "pain_in_hand",
    "douleur dans la main": "pain_in_hand",
    "mal aux mains": "pain_in_hand",
    "douleur_articulaire": "joint_pain",
    "douleur aux articulations": "joint_pain",
    "mal au dos": "back_pain",
    "douleur_dos": "back_pain",
    "mal au ventre": "stomach_pain",
    "douleur abdominale": "stomach_pain",
    # EN variants
    "chest pain": "chest_pain",
    "shortness of breath": "shortness_of_breath",
    "loss of consciousness": "loss_of_consciousness",
    "high fever": "high_fever",
    "severe trauma": "trauma",
    "pain in hand": "pain_in_hand",
    "hand pain": "pain_in_hand",
    "pain in my hand": "pain_in_hand",
    "joint pain": "joint_pain",
    "back pain": "back_pain",
    "stomach pain": "stomach_pain",
    "abdominal pain": "stomach_pain",
}


def _normalize_symptom(symptom: str) -> str:
    txt = unicodedata.normalize("NFKD", str(symptom)).encode("ascii", "ignore").decode("ascii")
    txt = txt.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in txt:
        txt = txt.replace("__", "_")
    return SYMPTOM_ALIASES.get(txt, txt)


def compute_score(symptoms: list[str], pain_level: int = 0, age: int = 30, is_conscious: bool = True) -> float:
    """
    Calcule un score de gravité normalisé entre 0 et 100.

    Args:
        symptoms:     Liste de symptômes du patient.
        pain_level:   Niveau de douleur [0-10].
        age:          Âge du patient.
        is_conscious: État de conscience du patient.

    Returns:
        Score float entre 0.0 et 100.0.
        
    Raises:
        ValueError: Si les paramètres sont invalides.
    """
    # Validation des entrées
    if not symptoms:
        raise ValueError("La liste des symptômes ne peut pas être vide")
    
    if not 0 <= pain_level <= 10:
        raise ValueError("Le niveau de douleur doit être entre 0 et 10")
    
    if not 0 <= age <= 150:
        raise ValueError("L'âge doit être entre 0 et 150 ans")
    
    score = 0.0
    critical_symptoms_found = []

    seen: set[str] = set()
    for symptom in symptoms:
        token = _normalize_symptom(symptom)
        if not token or token in seen:
            continue
        seen.add(token)
        
        # Vérification des symptômes critiques
        symptom_weight = SYMPTOM_WEIGHTS.get(token)
        if symptom_weight is None:
            # Pour les symptômes inconnus, utiliser un poids par défaut mais logger un avertissement
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Symptôme inconnu détecté: '{symptom}' -> '{token}'")
            symptom_weight = 5.0  # Poids modéré pour les symptômes inconnus
        
        score += symptom_weight
        
        # Suivi des symptômes critiques pour alerte
        if symptom_weight >= 50.0:
            critical_symptoms_found.append(symptom)

    # Ajout du score de douleur (sauf si inconscient)
    if is_conscious:
        score += pain_level * PAIN_WEIGHT
    else:
        # Pénalité pour inconscience
        score += 30.0

    # Ajustements liés à l'âge
    if age > AGE_THRESHOLD_HIGH:
        score += 10.0
    elif age < AGE_THRESHOLD_LOW:
        score += 10.0

    # Score final borné à 100
    final_score = min(round(score, 2), 100.0)
    
    # Log des cas critiques
    if critical_symptoms_found:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Symptômes critiques détectés: {critical_symptoms_found} -> Score: {final_score}")
    
    return final_score


def severity_label(score: float) -> str:
    """Retourne un label lisible selon le score."""
    if score >= 70:
        return "CRITIQUE"
    if score >= 40:
        return "SÉVÈRE"
    if score >= 20:
        return "MODÉRÉ"
    return "FAIBLE"
