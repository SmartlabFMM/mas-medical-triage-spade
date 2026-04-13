"""
train.py — Script d'entraînement autonome du modèle TriageAI.

Usage :
  # Données synthétiques (défaut)
  python train.py

  # Avec un CSV Kaggle
  python train.py --csv data/symptom_disease.csv --model gradient_boosting

  # Test de prédiction après entraînement
  python train.py --test
"""
import sys, os, logging
# Add project root to path to find core.triage_ai
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")

import argparse
from core.triage_ai import (
    generate_synthetic_dataset,
    load_kaggle_dataset,
    train_model,
    TriageAI,
)


def run_tests(ai: TriageAI):
    """Lance des tests de prédiction sur des cas connus."""
    test_cases = [
        {
            "desc":     "Patient critique — arrêt cardiaque probable",
            "symptoms": ["chest_pain", "loss_of_consciousness", "cold_sweat", "irregular_heartbeat"],
            "pain":     10,
            "expected": "hospitaliser",
        },
        {
            "desc":     "Patient modéré — gastro",
            "symptoms": ["nausea", "vomiting", "diarrhea", "fever"],
            "pain":     4,
            "expected": "surveiller",
        },
        {
            "desc":     "Patient léger — rhume",
            "symptoms": ["cough", "headache", "fatigue"],
            "pain":     2,
            "expected": "retour_domicile",
        },
    ]

    print("\n" + "="*60)
    print("  TESTS DE PRÉDICTION")
    print("="*60)

    ok_count = 0
    for tc in test_cases:
        result = ai.predict(tc["symptoms"], pain_level=tc["pain"])
        action = result["decision"]["action"]
        match  = "✓" if action == tc["expected"] else "✗"
        ok_count += 1 if action == tc["expected"] else 0

        print(f"\n  {match} {tc['desc']}")
        print(f"    Score    : {result['severity_score']:.1f}/100")
        print(f"    Décision : {action}  (attendu: {tc['expected']})")
        print(f"    Top SHAP :")
        for f in result["explanation"][:3]:
            print(f"      {f['symptom']:30s} {f['impact']:+.2f}")

    print(f"\n  Résultat : {ok_count}/{len(test_cases)} tests réussis")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(description="TriageAI — Entraînement")
    parser.add_argument("--csv",     default=None,            help="CSV Kaggle")
    parser.add_argument("--model",   default="random_forest", help="random_forest|gradient_boosting")
    parser.add_argument("--samples", type=int, default=3000,  help="Nb échantillons synthétiques")
    parser.add_argument("--test",    action="store_true",     help="Lancer les tests après")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("  TriageAI — Pipeline ML + SHAP")
    print("="*60)

    # Chargement données
    if args.csv and os.path.exists(args.csv):
        print(f"\n  Chargement CSV : {args.csv}")
        df = load_kaggle_dataset(args.csv)
    else:
        if args.csv:
            print(f"\n  ⚠ CSV introuvable : {args.csv}")
        print(f"\n  Génération {args.samples} patients synthétiques...")
        df = generate_synthetic_dataset(n_samples=args.samples)

    print(f"  Dataset : {len(df)} lignes × {len(df.columns)} colonnes")
    print(f"  Score moyen : {df['severity_score'].mean():.1f}/100")

    # Entraînement
    print(f"\n  Entraînement ({args.model})...")
    result = train_model(df, model_type=args.model, save=True)

    print(f"\n  ✓ Modèle sauvegardé → core/model.pkl")
    print(f"  MAE : {result['mae']:.2f} points")
    print(f"  R²  : {result['r2']:.3f}")

    # Tests optionnels
    if args.test:
        ai = TriageAI()
        run_tests(ai)


if __name__ == "__main__":
    main()
