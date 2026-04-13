"""
utils/helpers.py — Fonctions utilitaires génériques.
"""
from __future__ import annotations
import uuid
from datetime import datetime


def uuid_gen() -> str:
    """Génère un identifiant unique."""
    return str(uuid.uuid4())


def timestamp_now() -> str:
    """Retourne un timestamp lisible."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_decision_report(decision) -> str:
    """Formate une décision pour affichage console."""
    return decision.to_report()


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Limite une valeur entre min et max."""
    return max(min_val, min(max_val, value))
