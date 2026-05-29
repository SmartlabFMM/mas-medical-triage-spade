"""
models/triage_decision.py — Décision finale de triage émise par le Meta-Agent.
Traçable et journalisée pour audit (ENF-FIAB-03, EF-META-04).
"""
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, Field
from models.clinical_option import ActionType


class TriageDecision(BaseModel):
    """Décision finale documentée et traçable du cycle de triage."""

    patient_id: str
    severity_score: float = Field(..., ge=0.0, le=100.0)
    action: ActionType
    rationale: str        = Field(..., description="Justification de la décision finale")
    timestamp: datetime   = Field(default_factory=datetime.now)
    cycle_count: int      = Field(default=1, ge=1, description="Nombre de cycles de réévaluation")
    decided_by: str       = Field(default="MetaAgent")

    def to_report(self) -> str:
        return (
            f"[DÉCISION TRIAGE] {self.timestamp.strftime('%H:%M:%S')}\n"
            f"  Patient  : {self.patient_id}\n"
            f"  Gravité  : {self.severity_score:.1f}/100\n"
            f"  Action   : {self.action.value.upper()}\n"
            f"  Cycles   : {self.cycle_count}\n"
            f"  Raison   : {self.rationale}\n"
        )
