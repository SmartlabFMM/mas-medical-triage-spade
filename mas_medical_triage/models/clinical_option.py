"""
models/clinical_option.py — Options thérapeutiques générées par l'agent clinique BDI.
Chaque option est évaluée par un score d'utilité (EF-CLI-03).
"""
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    HOSPITALIZE = "hospitaliser"
    WATCH       = "surveiller"
    TRANSFER    = "transférer"


class ClinicalOption(BaseModel):
    """Une option thérapeutique proposée par l'agent clinique."""

    action: ActionType
    utility_score: float = Field(..., ge=0.0, le=1.0, description="Score d'utilité [0-1]")
    rationale: str = Field(..., description="Justification clinique")
    urgency_level: int = Field(..., ge=1, le=5, description="Niveau d'urgence 1=faible 5=critique")

    def __lt__(self, other: "ClinicalOption") -> bool:
        return self.utility_score < other.utility_score
