"""
core/triage_ai.py — Pipeline ML + SHAP pour le Système de Tri Médical.

Architecture :
  symptoms (list) → binary features → RandomForest → severity score (0-100)
                                                    ↓
                                               SHAP values → explanation JSON

Installation requise :
  pip install scikit-learn shap pandas numpy joblib
"""
from __future__ import annotations
import os
import json
import logging
import warnings
import unicodedata
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import MultiLabelBinarizer

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP non installé — pip install shap. Fallback sur feature_importances_.")

logger = logging.getLogger(__name__)

# ── Chemins ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")
META_PATH  = os.path.join(BASE_DIR, "model_meta.json")

# ── Mapping maladie → score de gravité (0–100) ────────────────────────────────
# Utilisé pour créer y quand le dataset n'a pas de colonne severity.
DISEASE_SEVERITY_MAP = {
    # Critique (70–100)
    "heart attack":          95, "cardiac arrest":       100,
    "stroke":                90, "pulmonary embolism":    88,
    "meningitis":            85, "sepsis":                92,
    "anaphylaxis":           88, "internal bleeding":     87,
    "aortic aneurysm":       93, "spinal cord injury":    82,
    # Sévère (40–69)
    "pneumonia":             65, "appendicitis":          62,
    "kidney failure":        70, "liver cirrhosis":       68,
    "diabetes type 1":       55, "tuberculosis":          60,
    "urinary tract infection":42, "bronchitis":           45,
    "hypoglycemia":          58, "hypertension":          50,
    # Modéré (20–39)
    "gastroenteritis":       30, "flu":                   28,
    "migraine":              25, "arthritis":             22,
    "asthma":                38, "anemia":                32,
    "hypothyroidism":        27, "depression":            24,
    # Faible (0–19)
    "common cold":           12, "allergy":               10,
    "fatigue":               8,  "back pain":             15,
    "skin rash":             11, "headache":              14,
}

# ── Liste complète des symptômes connus ───────────────────────────────────────
ALL_SYMPTOMS = sorted([
    "fever", "cough", "chest_pain", "shortness_of_breath", "headache",
    "fatigue", "nausea", "vomiting", "diarrhea", "abdominal_pain",
    "back_pain", "joint_pain", "muscle_pain", "dizziness", "loss_of_consciousness",
    "palpitations", "sweating", "chills", "weight_loss", "loss_of_appetite",
    "swollen_lymph_nodes", "skin_rash", "itching", "yellowing_of_skin",
    "dark_urine", "blurred_vision", "ringing_ears", "difficulty_swallowing",
    "excessive_thirst", "frequent_urination", "blood_in_urine", "bleeding",
    "stiff_neck", "high_fever", "confusion", "seizures", "paralysis",
    "fast_heart_rate", "irregular_heartbeat", "swollen_legs", "cold_sweat",
])

# Alias/synonymes (FR/EN) -> feature canonicale
SYMPTOM_ALIASES = {
    "douleur_thoracique": "chest_pain",
    "difficulte_respiratoire": "shortness_of_breath",
    "difficultes_respiratoires": "shortness_of_breath",
    "essoufflement": "shortness_of_breath",
    "fievre_elevee": "high_fever",
    "fievre": "fever",
    "perte_de_conscience": "loss_of_consciousness",
    "mal_de_tete": "headache",
    "nausee": "nausea",
    "vomissements": "vomiting",
    "trauma_cranien": "confusion",
    "hemorragie": "bleeding",
    "brulure_grave": "skin_rash",
    "hypoglycemie": "excessive_thirst",
    "avc": "stroke",
    "vertiges": "dizziness",
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. GÉNÉRATION DU DATASET SYNTHÉTIQUE (si pas de CSV disponible)
# ══════════════════════════════════════════════════════════════════════════════

def generate_synthetic_dataset(n_samples: int = 2000) -> pd.DataFrame:
    """
    Génère un dataset synthétique réaliste :
    colonnes = symptômes binaires + colonne 'severity_score'.

    Utilisé si aucun fichier CSV n'est fourni.
    """
    np.random.seed(42)
    records = []

    symptom_severity_weights = {
        "chest_pain":          35, "loss_of_consciousness": 40,
        "shortness_of_breath": 30, "bleeding":              35,
        "seizures":            38, "confusion":             28,
        "high_fever":          22, "fast_heart_rate":       18,
        "irregular_heartbeat": 20, "cold_sweat":            15,
        "fever":               12, "cough":                  8,
        "nausea":               8, "vomiting":              10,
        "headache":             8, "fatigue":                6,
        "dizziness":           10, "abdominal_pain":        12,
        "joint_pain":           7, "muscle_pain":            6,
        "skin_rash":            5, "back_pain":              6,
        "weight_loss":         10, "blurred_vision":         8,
        "excessive_thirst":     9, "frequent_urination":     7,
    }

    for _ in range(n_samples):
        row = {sym: 0 for sym in ALL_SYMPTOMS}

        # Sélection aléatoire de 1 à 6 symptômes avec biais de fréquence
        n_syms = np.random.choice([1, 2, 3, 4, 5, 6], p=[0.15, 0.25, 0.30, 0.20, 0.07, 0.03])
        chosen = np.random.choice(ALL_SYMPTOMS, size=n_syms, replace=False)
        for s in chosen:
            row[s] = 1

        # Score basé sur les poids + niveau de douleur simulé + bruit
        pain = np.random.randint(0, 11)
        base_score = sum(symptom_severity_weights.get(s, 5) for s in chosen)
        base_score += pain * 3
        base_score += np.random.normal(0, 6)  # bruit réaliste
        row["severity_score"] = float(np.clip(round(base_score), 0, 100))

        records.append(row)

    df = pd.DataFrame(records)
    logger.info(f"Dataset synthétique généré : {len(df)} échantillons, "
                f"{len(ALL_SYMPTOMS)} features, "
                f"score moyen={df['severity_score'].mean():.1f}")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 2. CHARGEMENT ET PRÉTRAITEMENT D'UN CSV KAGGLE
# ══════════════════════════════════════════════════════════════════════════════

def load_kaggle_dataset(csv_path: str) -> pd.DataFrame:
    """
    Charge un dataset Kaggle avec colonnes 'Symptom_1', 'Symptom_2'... et 'Disease'.
    Compatible avec le dataset 'disease_symptom_and_patient_profile_dataset'.

    Returns:
        DataFrame avec colonnes binaires par symptôme + severity_score.
    """
    df_raw = pd.read_csv(csv_path)
    df_raw.columns = [c.strip().lower().replace(" ", "_") for c in df_raw.columns]

    # Collecte les colonnes symptômes (Symptom_1, Symptom_2, ...)
    sym_cols = [c for c in df_raw.columns if "symptom" in c and c != "disease"]

    if not sym_cols:
        raise ValueError("Aucune colonne symptôme trouvée. Vérifiez le format du CSV.")

    # Aplatit les symptômes par ligne
    def get_symptoms(row):
        syms = []
        for col in sym_cols:
            val = str(row.get(col, "")).strip().lower()
            if val and val not in ("nan", "none", ""):
                syms.append(val.replace(" ", "_"))
        return syms

    df_raw["symptoms_list"] = df_raw.apply(get_symptoms, axis=1)

    # One-hot encoding
    mlb = MultiLabelBinarizer()
    sym_matrix = mlb.fit_transform(df_raw["symptoms_list"])
    sym_df = pd.DataFrame(sym_matrix, columns=mlb.classes_)

    # Crée le score depuis le mapping maladie
    if "disease" in df_raw.columns:
        disease_col = df_raw["disease"].str.lower().str.strip()
        scores = disease_col.map(DISEASE_SEVERITY_MAP)
        scores = scores.fillna(30)   # défaut si maladie inconnue
        # Ajoute du bruit pour éviter la surapprentissage
        scores = (scores + np.random.normal(0, 5, size=len(scores))).clip(0, 100)
    elif "severity" in df_raw.columns:
        scores = pd.to_numeric(df_raw["severity"], errors="coerce").fillna(30)
    else:
        scores = pd.Series([30.0] * len(df_raw))

    sym_df["severity_score"] = scores.values
    logger.info(f"Dataset Kaggle chargé : {len(sym_df)} lignes, "
                f"{len(mlb.classes_)} symptômes")
    return sym_df


# ══════════════════════════════════════════════════════════════════════════════
# 3. ENTRAÎNEMENT DU MODÈLE
# ══════════════════════════════════════════════════════════════════════════════

def train_model(
    df: pd.DataFrame,
    model_type: str = "random_forest",
    save: bool = True,
) -> dict:
    """
    Entraîne un modèle de régression symptoms → severity_score.

    Args:
        df:         DataFrame avec colonnes binaires + severity_score.
        model_type: 'random_forest' | 'gradient_boosting'
        save:       Si True, sauvegarde model.pkl et model_meta.json

    Returns:
        dict avec metrics, feature_names, model.
    """
    # ── Préparation X / y ─────────────────────────────────────────────────────
    feature_cols = [c for c in df.columns if c != "severity_score"]
    X = df[feature_cols].fillna(0).astype(float)
    y = df["severity_score"].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    # ── Choix du modèle ───────────────────────────────────────────────────────
    if model_type == "gradient_boosting":
        model = GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.08,
            subsample=0.85, random_state=42,
        )
    else:  # random_forest (défaut)
        model = RandomForestRegressor(
            n_estimators=200, max_depth=10, min_samples_leaf=3,
            n_jobs=-1, random_state=42,
        )

    model.fit(X_train, y_train)

    # ── Évaluation ────────────────────────────────────────────────────────────
    y_pred = model.predict(X_test)
    mae    = mean_absolute_error(y_test, y_pred)
    r2     = r2_score(y_test, y_pred)

    logger.info(f"Modèle entraîné ({model_type}) | MAE={mae:.2f} | R²={r2:.3f}")
    print(f"\n{'='*50}")
    print(f"  Modèle : {model_type}")
    print(f"  MAE    : {mae:.2f} points")
    print(f"  R²     : {r2:.3f}  (1.0 = parfait)")
    print(f"  Features: {len(feature_cols)}")
    print(f"{'='*50}\n")

    # ── Sauvegarde ────────────────────────────────────────────────────────────
    if save:
        joblib.dump(model, MODEL_PATH)
        meta = {
            "model_type":    model_type,
            "feature_names": feature_cols,
            "mae":           round(mae, 3),
            "r2":            round(r2, 3),
            "n_samples":     len(df),
            "n_features":    len(feature_cols),
        }
        with open(META_PATH, "w") as f:
            json.dump(meta, f, indent=2)
        logger.info(f"Modèle sauvegardé → {MODEL_PATH}")

    return {
        "model":         model,
        "feature_names": feature_cols,
        "mae":           mae,
        "r2":            r2,
    }


# ══════════════════════════════════════════════════════════════════════════════
# 4. CLASSE PRINCIPALE — TriageAI
# ══════════════════════════════════════════════════════════════════════════════

class TriageAI:
    """
    Moteur d'intelligence artificielle du système de triage.

    Usage :
        ai = TriageAI()
        result = ai.predict(["fever", "chest_pain"], pain_level=7)
        # → {"score": 78, "decision": "hospitaliser", "explanation": [...]}
    """

    def __init__(self):
        self.model         = None
        self.feature_names = []
        self.explainer     = None
        self._load_or_train()

    # ── Chargement / initialisation ───────────────────────────────────────────

    def _load_or_train(self):
        """Charge le modèle existant ou entraîne un nouveau."""
        if os.path.exists(MODEL_PATH) and os.path.exists(META_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                with open(META_PATH) as f:
                    meta = json.load(f)
                self.feature_names = meta["feature_names"]
                logger.info(f"Modèle chargé depuis {MODEL_PATH} "
                            f"(R²={meta.get('r2', '?')})")
                self._init_explainer()
                return
            except Exception as e:
                logger.warning(f"Impossible de charger le modèle : {e}. Ré-entraînement...")

        # Ré-entraîne sur données synthétiques
        logger.info("Entraînement sur données synthétiques...")
        df = generate_synthetic_dataset(n_samples=3000)
        result = train_model(df, model_type="random_forest", save=True)
        self.model         = result["model"]
        self.feature_names = result["feature_names"]
        self._init_explainer()

    def _init_explainer(self):
        """Initialise l'explainer SHAP."""
        if not SHAP_AVAILABLE:
            return
        try:
            self.explainer = shap.TreeExplainer(self.model)
            logger.info("SHAP TreeExplainer initialisé")
        except Exception as e:
            logger.warning(f"Impossible d'initialiser SHAP : {e}")

    # ── Vectorisation des symptômes ───────────────────────────────────────────

    def _vectorize(self, symptoms: list[str], pain_level: int = 0) -> np.ndarray:
        """
        Convertit une liste de symptômes en vecteur binaire.

        Args:
            symptoms:   ['fever', 'chest_pain', ...]
            pain_level: 0–10 (non utilisé directement en feature mais
                        influence le score via le modèle pré-entraîné)

        Returns:
            np.ndarray shape (1, n_features)
        """
        vec = np.zeros(len(self.feature_names))

        def _norm(sym: str) -> str:
            txt = unicodedata.normalize("NFKD", str(sym)).encode("ascii", "ignore").decode("ascii")
            txt = txt.strip().lower().replace(" ", "_").replace("-", "_")
            while "__" in txt:
                txt = txt.replace("__", "_")
            return txt

        normalized = []
        for s in symptoms:
            token = _norm(s)
            token = SYMPTOM_ALIASES.get(token, token)
            normalized.append(token)

        for sym in normalized:
            if sym in self.feature_names:
                idx = self.feature_names.index(sym)
                vec[idx] = 1
            else:
                # Recherche partielle (ex: "chest pain" → "chest_pain")
                for i, feat in enumerate(self.feature_names):
                    if sym in feat or feat in sym:
                        vec[i] = 1
                        break

        return vec.reshape(1, -1)

    # ── Prédiction SHAP ───────────────────────────────────────────────────────

    def _shap_explanation(
        self,
        X_vec: np.ndarray,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Calcule les valeurs SHAP et retourne les top_k facteurs.

        Returns:
            [{"symptom": "chest_pain", "impact": 25.3, "present": True}, ...]
        """
        # ── SHAP disponible ───────────────────────────────────────────────────
        if SHAP_AVAILABLE and self.explainer is not None:
            try:
                shap_values = self.explainer.shap_values(X_vec)
                if isinstance(shap_values, list):
                    shap_values = shap_values[0]  # Pour classifieurs multi-output
                sv = shap_values[0]  # shape (n_features,)

                factors = []
                for i, val in enumerate(sv):
                    if abs(val) > 0.01:  # filtre les valeurs négligeables
                        factors.append({
                            "symptom": self.feature_names[i].replace("_", " "),
                            "impact":  round(float(val), 2),
                            "present": bool(X_vec[0, i] > 0),
                        })

                # Trie par impact absolu décroissant
                factors.sort(key=lambda x: abs(x["impact"]), reverse=True)
                return factors[:top_k]

            except Exception as e:
                logger.warning(f"SHAP calcul échoué : {e}. Fallback feature importance.")

        # ── Fallback : feature importances du RandomForest ───────────────────
        importances = self.model.feature_importances_
        X_flat = X_vec[0]
        factors = []
        for i, (feat, imp) in enumerate(zip(self.feature_names, importances)):
            if X_flat[i] > 0 and imp > 0:
                # Impact approximé : importance × score moyen de contribution
                factors.append({
                    "symptom": feat.replace("_", " "),
                    "impact":  round(float(imp * 30), 2),  # scaled to ~score range
                    "present": True,
                })

        factors.sort(key=lambda x: abs(x["impact"]), reverse=True)
        return factors[:top_k]

    # ── Logique de décision ───────────────────────────────────────────────────

    @staticmethod
    def score_to_decision(score: float) -> dict:
        """
        Convertit le score de gravité en décision clinique.

        Returns:
            {"action": "hospitaliser", "urgency": "critique", "color": "#dc2626"}
        """
        if score >= 70:
            return {
                "action":       "hospitaliser",
                "urgency":      "critique",
                "label":        "HOSPITALISATION IMMÉDIATE",
                "color":        "#dc2626",
                "instructions": "Patient à prendre en charge immédiatement. Alerte le service concerné.",
            }
        elif score >= 40:
            return {
                "action":       "surveiller",
                "urgency":      "modéré",
                "label":        "SURVEILLANCE MÉDICALE",
                "color":        "#d97706",
                "instructions": "Placer en observation. Réévaluation dans 30 minutes.",
            }
        else:
            return {
                "action":       "retour_domicile",
                "urgency":      "faible",
                "label":        "RETOUR À DOMICILE",
                "color":        "#059669",
                "instructions": "Prescrire traitement symptomatique. Consulter si aggravation.",
            }

    # ── Prédiction principale ─────────────────────────────────────────────────

    def predict(
        self,
        symptoms:    list[str],
        pain_level:  int = 0,
        patient_id:  str = "",
        top_k:       int = 5,
    ) -> dict:
        """
        Pipeline complet : symptoms → score → decision → SHAP explanation.

        Args:
            symptoms:   Liste des symptômes déclarés.
            pain_level: Niveau de douleur 0–10.
            patient_id: ID patient pour le logging.
            top_k:      Nombre de facteurs SHAP à retourner.

        Returns:
            {
                "severity_score": 78.4,
                "decision": {...},
                "explanation": [{"symptom": "chest_pain", "impact": 25.3, "present": True}],
                "symptoms_found": ["chest_pain", "fever"],
                "symptoms_unknown": ["some_symptom"],
            }
        """
        if self.model is None:
            raise RuntimeError("Modèle non initialisé.")

        # Vectorisation
        X_vec = self._vectorize(symptoms, pain_level)

        # Correction avec le pain_level (bonus brut)
        base_score = float(self.model.predict(X_vec)[0])
        pain_bonus = pain_level * 1.5  # +1.5 points par niveau de douleur
        score = float(np.clip(base_score + pain_bonus, 0, 100))

        # Décision
        decision = self.score_to_decision(score)

        # SHAP / feature importance
        explanation = self._shap_explanation(X_vec, top_k=top_k)

        # Audit : symptômes reconnus vs inconnus
        normalized = [s.strip().lower().replace(" ", "_") for s in symptoms]
        found   = [s for s in normalized if s in self.feature_names]
        unknown = [s for s in normalized if s not in self.feature_names]

        result = {
            "severity_score":    round(score, 1),
            "decision":          decision,
            "explanation":       explanation,
            "symptoms_found":    found,
            "symptoms_unknown":  unknown,
            "model_confidence":  self._confidence(score),
        }

        logger.info(
            f"[TriageAI] patient={patient_id or '?'} | "
            f"symptoms={len(found)} | score={score:.1f} | "
            f"action={decision['action']}"
        )
        return result

    def _confidence(self, score: float) -> str:
        """Niveau de confiance qualitatif basé sur le score."""
        if 30 <= score <= 70:
            return "modérée"   # zone ambiguë
        return "élevée"

    # ── Ré-entraînement à la demande ─────────────────────────────────────────

    def retrain(
        self,
        csv_path:   str | None = None,
        model_type: str = "random_forest",
        n_samples:  int = 3000,
    ) -> dict:
        """
        Ré-entraîne le modèle et recharge l'explainer.

        Args:
            csv_path:   Chemin vers un CSV Kaggle (None = données synthétiques).
            model_type: 'random_forest' | 'gradient_boosting'
            n_samples:  Nombre d'échantillons synthétiques si pas de CSV.

        Returns:
            dict avec les métriques du nouveau modèle.
        """
        if csv_path and os.path.exists(csv_path):
            df = load_kaggle_dataset(csv_path)
        else:
            df = generate_synthetic_dataset(n_samples=n_samples)

        result = train_model(df, model_type=model_type, save=True)
        self.model         = result["model"]
        self.feature_names = result["feature_names"]
        self._init_explainer()

        return {
            "status":     "ok",
            "model_type": model_type,
            "mae":        round(result["mae"], 3),
            "r2":         round(result["r2"], 3),
            "n_samples":  len(df),
            "n_features": len(self.feature_names),
        }

    # ── Infos modèle ──────────────────────────────────────────────────────────

    def model_info(self) -> dict:
        """Retourne les infos du modèle chargé."""
        if not os.path.exists(META_PATH):
            return {"status": "no model loaded"}
        with open(META_PATH) as f:
            meta = json.load(f)
        meta["shap_available"]  = SHAP_AVAILABLE
        meta["model_loaded"]    = self.model is not None
        meta["explainer_ready"] = self.explainer is not None
        return meta


# ── Singleton global ──────────────────────────────────────────────────────────
# Importé et utilisé par app.py
_triage_ai_instance: TriageAI | None = None

def get_triage_ai() -> TriageAI:
    """Retourne l'instance singleton du moteur IA (lazy init)."""
    global _triage_ai_instance
    if _triage_ai_instance is None:
        _triage_ai_instance = TriageAI()
    return _triage_ai_instance


# ── Script autonome : entraînement ───────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")

    parser = argparse.ArgumentParser(description="TriageAI — Entraînement du modèle")
    parser.add_argument("--csv",     default=None,            help="Chemin vers un CSV Kaggle")
    parser.add_argument("--model",   default="random_forest", help="random_forest | gradient_boosting")
    parser.add_argument("--samples", type=int, default=3000,  help="Nb échantillons synthétiques")
    args = parser.parse_args()

    print("\n=== TriageAI — Entraînement du modèle de triage ===\n")

    if args.csv:
        df = load_kaggle_dataset(args.csv)
    else:
        print(f"Génération de {args.samples} patients synthétiques...")
        df = generate_synthetic_dataset(n_samples=args.samples)

    result = train_model(df, model_type=args.model, save=True)

    # Test de prédiction
    ai = TriageAI()
    test = ai.predict(["chest_pain", "shortness_of_breath", "cold_sweat"], pain_level=8)
    print("\n=== Test de prédiction ===")
    print(f"Score    : {test['severity_score']}/100")
    print(f"Décision : {test['decision']['label']}")
    print(f"Top facteurs SHAP :")
    for f in test["explanation"]:
        sign = "+" if f["impact"] > 0 else ""
        print(f"  {f['symptom']:30s} {sign}{f['impact']:+.1f}")
