"""
simulation/run_scenarios.py — Exécution locale des scénarios de test.
Charge chaque fichier JSON, calcule le score de gravité et affiche
un rapport de triage complet. (Phase 4 CDC — Validation)

Usage :
    python -m simulation.run_scenarios                        # tous les scénarios
    python -m simulation.run_scenarios scenario_avc           # un seul scénario
    python -m simulation.run_scenarios scenario_avc scenario_trauma  # plusieurs
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

from utils.severity_calculator import compute_score, severity_label

SCENARIOS_DIR = Path(__file__).parent / "scenarios"

# Fix encodage Windows (cp1252 → UTF-8)
sys.stdout.reconfigure(encoding="utf-8")

# ── Couleurs ANSI ──────────────────────────────────────────────────
RED    = "\033[91m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"


def color_for_label(label: str) -> str:
    """Retourne la couleur ANSI associée au niveau de gravité."""
    return {
        "CRITIQUE": RED,
        "SÉVÈRE":   YELLOW,
        "MODÉRÉ":   CYAN,
        "FAIBLE":   GREEN,
    }.get(label, RESET)


def load_scenario(name: str) -> list[dict]:
    """Charge un fichier scénario JSON."""
    path = SCENARIOS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scénario introuvable : {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def triage_patient(data: dict) -> dict:
    """Calcule le triage pour un patient à partir de ses données brutes."""
    score = compute_score(
        symptoms=data["symptoms"],
        pain_level=data.get("pain_level", 0),
        age=data.get("age", 30),
    )
    label = severity_label(score)

    # Déterminer l'action recommandée
    if score >= 70:
        action = "HOSPITALISER"
    elif score >= 40:
        action = "SURVEILLER"
    else:
        action = "RENVOYER / CONSULTATION"

    return {
        "name": data["name"],
        "age": data["age"],
        "gender": data.get("gender", "?"),
        "symptoms": data["symptoms"],
        "pain_level": data.get("pain_level", 0),
        "is_conscious": data.get("is_conscious", True),
        "score": score,
        "label": label,
        "action": action,
    }


def run_one_scenario(name: str) -> list[dict]:
    """Exécute un scénario et affiche les résultats."""
    patients_data = load_scenario(name)
    results = [triage_patient(p) for p in patients_data]

    # Trier par score décroissant (les plus graves en premier)
    results.sort(key=lambda r: r["score"], reverse=True)

    # ── Affichage ──────────────────────────────────────────────────
    header = f"  SCÉNARIO : {name.upper()}  "
    print(f"\n{BOLD}{'═' * 70}")
    print(f"  {header}")
    print(f"{'═' * 70}{RESET}")
    print(f"{DIM}  {len(results)} patient(s) • {datetime.now().strftime('%H:%M:%S')}{RESET}\n")

    for i, r in enumerate(results, 1):
        color = color_for_label(r["label"])
        conscious = "✓ conscient" if r["is_conscious"] else "✗ INCONSCIENT"

        print(f"  {BOLD}#{i}{RESET}  {r['name']} ({r['age']} ans, {r['gender']})")
        print(f"      Symptômes  : {', '.join(r['symptoms'])}")
        print(f"      Douleur    : {r['pain_level']}/10  •  {conscious}")
        print(f"      {color}{BOLD}Score      : {r['score']:.1f}/100  →  {r['label']}{RESET}")
        print(f"      Action     : {r['action']}")
        print()

    # ── Résumé ─────────────────────────────────────────────────────
    critiques = sum(1 for r in results if r["label"] == "CRITIQUE")
    severes   = sum(1 for r in results if r["label"] == "SÉVÈRE")
    moderes   = sum(1 for r in results if r["label"] == "MODÉRÉ")
    faibles   = sum(1 for r in results if r["label"] == "FAIBLE")

    print(f"  {DIM}{'─' * 60}{RESET}")
    print(f"  Résumé : {RED}{critiques} critique(s){RESET} • "
          f"{YELLOW}{severes} sévère(s){RESET} • "
          f"{CYAN}{moderes} modéré(s){RESET} • "
          f"{GREEN}{faibles} faible(s){RESET}")
    print(f"{BOLD}{'═' * 70}{RESET}\n")

    return results


def main() -> None:
    """Point d'entrée : exécute les scénarios spécifiés ou tous."""
    if len(sys.argv) > 1:
        scenario_names = sys.argv[1:]
    else:
        # Tous les scénarios trouvés dans le dossier
        scenario_names = sorted(
            p.stem for p in SCENARIOS_DIR.glob("scenario_*.json")
        )

    if not scenario_names:
        print("Aucun scénario trouvé dans", SCENARIOS_DIR)
        return

    print(f"\n{BOLD}{CYAN}╔{'═' * 68}╗")
    print(f"║  SIMULATION DE TRIAGE MÉDICAL — Phase 4 CDC{' ' * 23}║")
    print(f"╚{'═' * 68}╝{RESET}")

    all_results = {}
    for name in scenario_names:
        try:
            all_results[name] = run_one_scenario(name)
        except FileNotFoundError as e:
            print(f"\n  {RED}ERREUR : {e}{RESET}\n")

    # ── Bilan global ───────────────────────────────────────────────
    total = sum(len(r) for r in all_results.values())
    total_critiques = sum(
        1 for results in all_results.values()
        for r in results if r["label"] == "CRITIQUE"
    )
    print(f"{BOLD}{CYAN}┌{'─' * 68}┐")
    print(f"│  BILAN GLOBAL : {total} patients traités dans "
          f"{len(all_results)} scénario(s){' ' * (68 - 52 - len(str(total)) - len(str(len(all_results))))}│")
    print(f"│  Patients critiques : {total_critiques}/{total}"
          f"{' ' * (68 - 27 - len(str(total_critiques)) - len(str(total)))}│")
    print(f"└{'─' * 68}┘{RESET}\n")


if __name__ == "__main__":
    main()
