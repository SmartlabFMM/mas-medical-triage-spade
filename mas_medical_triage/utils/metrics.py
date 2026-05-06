"""
utils/metrics.py — Collecte des métriques de performance (ENF-TEST-03, ENF-PERF-01).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TriageMetrics:
    """Métriques de performance du système de triage."""

    total_patients: int       = 0
    decisions_made: int       = 0
    reevaluations: int        = 0
    conflicts_resolved: int   = 0
    cycle_times: list[float]  = field(default_factory=list)  # secondes
    started_at: datetime      = field(default_factory=datetime.now)

    def record_cycle(self, duration_seconds: float) -> None:
        self.cycle_times.append(duration_seconds)
        self.decisions_made += 1

    @property
    def avg_cycle_time(self) -> float:
        if not self.cycle_times:
            return 0.0
        return round(sum(self.cycle_times) / len(self.cycle_times), 3)

    @property
    def max_cycle_time(self) -> float:
        return max(self.cycle_times, default=0.0)

    @property
    def timeout_violations(self) -> int:
        """Nombre de cycles ayant dépassé 5 secondes (ENF-PERF-01)."""
        return sum(1 for t in self.cycle_times if t > 5.0)

    def summary(self) -> str:
        return (
            f"\n{'='*50}\n"
            f"  RAPPORT MÉTRIQUES\n"
            f"{'='*50}\n"
            f"  Patients traités  : {self.total_patients}\n"
            f"  Décisions émises  : {self.decisions_made}\n"
            f"  Réévaluations     : {self.reevaluations}\n"
            f"  Conflits résolus  : {self.conflicts_resolved}\n"
            f"  Temps moyen cycle : {self.avg_cycle_time}s\n"
            f"  Temps max cycle   : {self.max_cycle_time}s\n"
            f"  Violations 5s     : {self.timeout_violations}\n"
            f"{'='*50}\n"
        )


# Instance globale partagée
metrics = TriageMetrics()
