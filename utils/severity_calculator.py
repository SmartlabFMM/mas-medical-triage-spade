"""
utils/severity_calculator.py — Calcul du score de gravité médicale avancé.
Partagé entre agents sans duplication (SOLID). (EF-CLI-01)
Score de 0 (faible) à 100 (critique).

NOUVELLE LOGIQUE (v2.0):
- Score_symptôme = Poids × Intensité × Durée
- Multiplicateurs âge/conscience
- Court-circuit pour cas critiques
- Bonus pour cas urgents
"""
from __future__ import annotations
import unicodedata
from typing import TypedDict
import logging

logger = logging.getLogger(__name__)


class SymptomDetail(TypedDict, total=False):
    """Structure d'un symptôme avec détails."""
    name: str
    intensity: int  # 1=Faible, 2=Modéré, 3=Élevé
    duration: str   # "recente", "persistante", "chronique" ou format libre


# =============================================================================
# POIDS DES SYMPTÔMES (base)
# =============================================================================
SYMPTOM_WEIGHTS: dict[str, float] = {
    # === CRITIQUE (requiert prise en charge immédiate) ===
    "douleur thoracique":        40.0,
    "arrêt cardiaque":           100.0,
    "perte de conscience":       50.0,
    "difficulté respiratoire":   45.0,
    "avc":                       55.0,
    "convulsions":               48.0,
    "hémorragie":                50.0,
    "confusion":                 35.0,
    "respiration anormale":      45.0,
    "saignement abondant":       50.0,
    
    # === URGENT (nécessite attention rapide) ===
    "vomissements":              18.0,
    "douleur abdominale":        28.0,
    "fièvre élevée":             15.0,  
    "trauma":                    32.0,
    "trauma crânien":            38.0,
    "fracture ouverte":          33.0,
    "brûlure grave":             33.0,
    "hypoglycémie":              28.0,
    "déshydratation":            22.0,
    "douleur non localisée":     25.0,
    
    # === MODÉRÉ ===
    "fièvre":                    15.0,
    "douleur_main":              12.0,
    "douleur_articulaire":       15.0,
    "back_pain":                 18.0,
    "stomach_pain":              22.0,
    
    # === LÉGER ===
    "mal de tête":               20.0, 
    "toux":                       5.0,
    "douleur musculaire":         8.0,
    "nausée":                    10.0,
    "dizziness":                 10.0,
    
    # === CANONICAL EN TOKENS ===
    "chest_pain":                40.0,
    "shortness_of_breath":       45.0,
    "loss_of_consciousness":     50.0,
    "high_fever":                15.0,  
    "fever":                     15.0,
    "headache":                  20.0, 
    "nausea":                    10.0,
    "vomiting":                  18.0,
    "bleeding":                  50.0,
    "stroke":                    55.0,
    "severe_confusion":          35.0,
    "pain_in_hand":              12.0,
    "hand_pain":                 12.0,
    "joint_pain":                15.0,
    "muscle_pain":               8.0,
    "abdominal_pain":            28.0,
}


# =============================================================================
# FACTEURS MULTIPLICATIFS
# =============================================================================

# Intensité : multiplicateur selon le niveau
INTENSITY_FACTORS = {
    1: 1/3,     # Faible : 1/3 du score
    2: 2/3,     # Modéré : 2/3 du score
    3: 1.0,     # Élevé : score complet
}

# Durée : multiplicateur selon la durée
DURATION_FACTORS = {
    "recente": 1.0,       # < 24h
    "persistante": 1.2,   # 24h - 7j
    "chronique": 1.5,     # > 7j
}

# Facteurs de risque (multiplicateurs globaux)
AGE_RISK_MULTIPLIER = 1.2      # < 5 ans ou > 70 ans
CONSCIOUSNESS_MULTIPLIER = 1.5  # Inconscient

# Cas urgents (bonus)
URGENT_CASE_MULTIPLIER = 1.3


# =============================================================================
# CAS CRITIQUES (court-circuitent le calcul)
# =============================================================================
CRITICAL_SYMPTOMS = {
    "perte de conscience", "loss_of_consciousness",
    "convulsions", "seizure",
    "confusion sévère", "severe_confusion",
    "douleur thoracique", "chest_pain",  # Base + anglais
    "douleur thoracique intense", "severe_chest_pain",
    "difficulté respiratoire", "shortness_of_breath",  # Base + anglais
    "difficulté respiratoire importante", "severe_shortness_of_breath",
    "respiration anormale", "abnormal_breathing",
    "saignement abondant", "severe_bleeding",
    "hémorragie", "bleeding",
    "arrêt cardiaque", "cardiac_arrest",
    "avc", "stroke",
}

# =============================================================================
# CAS URGENTS (multiplicateur 1.3)
# =============================================================================
URGENT_SYMPTOMS = {
    "vomissements persistants", "persistent_vomiting",
    "douleur abdominale intense", "severe_abdominal_pain",
    "fièvre persistante", "persistent_fever",
    "traumatisme", "trauma",
    "chute", "fall",
    "accident", "accident",
    "douleur importante non localisée", "severe_unlocalized_pain",
    "fracture ouverte", "open_fracture",
    "brûlure grave", "severe_burn",
    "hypoglycémie", "hypoglycemia",
    "trauma crânien", "head_trauma",
    "déshydratation", "dehydration",
}


# =============================================================================
# ALIASES
# =============================================================================
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
    "nausée": "nausea",
    "nausee": "nausea",  # sans accent après normalisation
    "vomissements": "vomiting",
    "hemorragie": "bleeding",
    "trauma_cranien": "head_trauma",
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
    "douleur abdominale": "abdominal_pain",
    "confusion_severe": "severe_confusion",
    "douleur_intense": "severe_unlocalized_pain",
    "saignement": "bleeding",
    # EN variants
    "chest pain": "chest_pain",
    "shortness of breath": "shortness_of_breath",
    "loss of consciousness": "loss_of_consciousness",
    "high fever": "high_fever",
    "severe trauma": "trauma",
    "pain in hand": "pain_in_hand",
    "hand pain": "hand_pain",
    "pain in my hand": "pain_in_hand",
    "joint pain": "joint_pain",
    "back pain": "back_pain",
    "stomach pain": "stomach_pain",
    "abdominal pain": "abdominal_pain",
    "seizure": "convulsions",
    "severe bleeding": "severe_bleeding",
    "abnormal breathing": "respiration_anormale",
    "cardiac arrest": "arrêt cardiaque",
    "persistent vomiting": "vomissements persistants",
    "severe abdominal pain": "douleur abdominale intense",
    "persistent fever": "fièvre persistante",
    "fall": "chute",
    "head trauma": "trauma_cranien",
    "open fracture": "fracture ouverte",
    "severe burn": "brûlure grave",
}


def _normalize_symptom(symptom: str) -> str:
    txt = unicodedata.normalize("NFKD", str(symptom)).encode("ascii", "ignore").decode("ascii")
    txt = txt.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in txt:
        txt = txt.replace("__", "_")
    return SYMPTOM_ALIASES.get(txt, txt)


def _is_critical_symptom(symptom: str) -> bool:
    """Vérifie si un symptôme est critique (court-circuit)."""
    normalized = _normalize_symptom(symptom)
    return (
        normalized in CRITICAL_SYMPTOMS 
        or symptom.lower() in CRITICAL_SYMPTOMS
        or any(crit in symptom.lower() for crit in ["perte de conscience", "arrêt cardiaque", "convulsion", "saignement abondant"])
    )


def _is_urgent_symptom(symptom: str) -> bool:
    """Vérifie si un symptôme est urgent (multiplicateur)."""
    normalized = _normalize_symptom(symptom)
    # Normaliser aussi le symptôme original pour la comparaison de sous-chaînes
    normalized_original = unicodedata.normalize("NFKD", str(symptom)).encode("ascii", "ignore").decode("ascii").lower()
    return (
        normalized in URGENT_SYMPTOMS 
        or symptom.lower() in URGENT_SYMPTOMS
        or any(urg in normalized_original for urg in ["persistant", "intense", "trauma", "fracture", "brûlure", "severe"])
    )


def _parse_duration(duration: str) -> float:
    """Parse la durée et retourne le facteur multiplicateur."""
    if not duration:
        return 1.0
    
    duration_lower = duration.lower().strip()
    
    # Mapping direct
    if duration_lower in DURATION_FACTORS:
        return DURATION_FACTORS[duration_lower]
    
    # Parsing numérique
    try:
        # Extrait le nombre et l'unité
        import re
        match = re.match(r'(\d+)\s*(h|heure|heures|j|jour|jours|s|semaine|semaines|m|mois)', duration_lower)
        if match:
            value = int(match.group(1))
            unit = match.group(2)
            
            # Conversion en heures
            if unit in ['j', 'jour', 'jours']:
                hours = value * 24
            elif unit in ['s', 'semaine', 'semaines']:
                hours = value * 24 * 7
            elif unit in ['m', 'mois']:
                hours = value * 24 * 30
            else:  # heures
                hours = value
            
            # Classification
            if hours < 24:
                return 1.0  # Récente
            elif hours <= 24 * 7:
                return 1.2  # Persistante
            else:
                return 1.5  # Chronique
    except:
        pass
    
    return 1.0  # Par défaut


def compute_score(
    symptoms: list[str | SymptomDetail], 
    pain_level: int = 0, 
    age: int = 30, 
    is_conscious: bool = True,
    temperature: float | None = None
) -> dict:
    """
    Calcule un score de gravité avec la nouvelle logique clinique.
    
    Args:
        symptoms: Liste de symptômes (str ou dict avec name/intensity/duration)
        pain_level: Niveau de douleur général [0-10]
        age: Âge du patient
        is_conscious: État de conscience
        temperature: Température corporelle (optionnel, pour détecter fièvre critique)
    
    Returns:
        dict avec {
            'score': float (0-100),
            'raw_score': float (avant plafonnage),
            'classification': str ('léger', 'modéré', 'urgent', 'critique'),
            'is_critical': bool,
            'is_urgent': bool,
            'multiplier': float,
            'details': list[dict]  # détails par symptôme
        }
    """
    # Validation
    if not symptoms:
        raise ValueError("La liste des symptômes ne peut pas être vide")
    
    if not 0 <= pain_level <= 10:
        raise ValueError("Le niveau de douleur doit être entre 0 et 10")
    
    if not 0 <= age <= 150:
        raise ValueError("L'âge doit être entre 0 et 150 ans")
    
    # Vérification cas critiques (court-circuit)
    has_critical = False
    critical_symptoms_found = []
    
    for symptom in symptoms:
        symptom_name = symptom['name'] if isinstance(symptom, dict) else symptom
        if _is_critical_symptom(symptom_name):
            has_critical = True
            critical_symptoms_found.append(symptom_name)
    
    # Vérification température critique (> 40°C)
    has_high_fever = temperature is not None and temperature > 40.0
    if has_high_fever:
        has_critical = True
        critical_symptoms_found.append(f"fièvre très élevée ({temperature}°C)")
    
    # Si cas critique détecté, retourner immédiatement
    if has_critical:
        logger.warning(f"CAS CRITIQUE DÉTECTÉ: {critical_symptoms_found}")
        return {
            'score': 100.0,
            'raw_score': 100.0,
            'classification': 'critique',
            'is_critical': True,
            'is_urgent': False,
            'multiplier': 1.0,
            'details': [],
            'critical_symptoms': critical_symptoms_found,
            'message': 'Prise en charge immédiate requise'
        }
    
    # Calcul du score par symptôme
    total_score = 0.0
    details = []
    has_urgent = False
    
    seen: set[str] = set()
    
    for symptom in symptoms:
        # Extraction des données
        if isinstance(symptom, dict):
            symptom_name = symptom.get('name', '')
            intensity = symptom.get('intensity', 2)  # Modéré par défaut
            duration = symptom.get('duration', '')
        else:
            symptom_name = symptom
            intensity = 2  # Modéré par défaut
            duration = ''
        
        # Normalisation
        token = _normalize_symptom(symptom_name)
        if not token or token in seen:
            continue
        seen.add(token)
        
        # Poids de base
        base_weight = SYMPTOM_WEIGHTS.get(token)
        if base_weight is None:
            logger.warning(f"Symptôme inconnu: '{symptom_name}' -> '{token}', poids par défaut 10.0")
            base_weight = 10.0
        
        # Facteur d'intensité
        intensity_factor = INTENSITY_FACTORS.get(intensity, 2/3)
        
        # Facteur de durée
        duration_factor = _parse_duration(duration)
        
        # Score du symptôme
        symptom_score = base_weight * intensity_factor * duration_factor
        total_score += symptom_score
        
        # Vérification si symptôme urgent
        if _is_urgent_symptom(symptom_name):
            has_urgent = True
        
        # Détail pour debug
        details.append({
            'name': symptom_name,
            'normalized': token,
            'base_weight': base_weight,
            'intensity': intensity,
            'intensity_factor': intensity_factor,
            'duration': duration,
            'duration_factor': duration_factor,
            'score': round(symptom_score, 2)
        })
    
    # Multiplicateurs de risque
    risk_multiplier = 1.0
    
    # Âge à risque
    if age < 5 or age > 70:
        risk_multiplier *= AGE_RISK_MULTIPLIER
    
    # Inconscience
    if not is_conscious:
        risk_multiplier *= CONSCIOUSNESS_MULTIPLIER
    
    # Cas urgent
    if has_urgent:
        risk_multiplier *= URGENT_CASE_MULTIPLIER
    
    # Score brut (sans douleur générale - calcul basé uniquement sur les symptômes)
    raw_score = total_score * risk_multiplier
    
    # La douleur générale (pain_level) n'est plus ajoutée au score
    # Le score est calculé uniquement à partir des symptômes avec intensité et durée
    pain_contribution = 0.0
    
    final_score = raw_score
    
    # Plafonnement à 100
    final_score = min(round(final_score, 2), 100.0)
    
    # Classification
    classification = severity_label(final_score)
    
    logger.info(f"Score calculé: {final_score} ({classification}) - Multiplicateur: {risk_multiplier}")
    
    return {
        'score': final_score,
        'raw_score': round(raw_score, 2),
        'classification': classification,
        'is_critical': False,
        'is_urgent': has_urgent,
        'multiplier': round(risk_multiplier, 2),
        'details': details,
        'pain_contribution': pain_contribution,
        'critical_symptoms': [],
        'message': None
    }


def severity_label(score: float) -> str:
    """
    Retourne la classification selon le score.
    
    Nouveaux seuils:
    - 0-25: Léger
    - 26-50: Modéré
    - 51-75: Urgent
    - 76-100: Critique
    """
    if score > 75:
        return "critique"
    if score > 50:
        return "urgent"
    if score > 25:
        return "modéré"
    return "léger"


def get_recommended_action(classification: str) -> str:
    """Retourne l'action recommandée selon la classification."""
    actions = {
        'léger': 'À surveiller (retour à domicile)',
        'modéré': 'hospitalisation légère (médecin généraliste)',
        'urgent': 'Hospitalisation obligatoire',
        'critique': 'Hospitalisation prioritaire avec gestion de la priorité'
    }
    return actions.get(classification, 'Évaluation requise')


# =============================================================================
# FONCTIONS LEGACY (compatibilité)
# =============================================================================

def compute_score_legacy(symptoms: list[str], pain_level: int = 0, age: int = 30, is_conscious: bool = True) -> float:
    """Version legacy pour compatibilité (retourne juste le score)."""
    result = compute_score(symptoms, pain_level, age, is_conscious)
    return result['score']
