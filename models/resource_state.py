"""
models/resource_state.py — État temps réel des ressources hospitalières.
Maintenu par l'Agent Gestion des Ressources (EF-RES-01/02/03).
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class ResourceState(BaseModel):
    """Snapshot des ressources disponibles à un instant T."""

    beds_total: int     = Field(..., ge=0)
    beds_available: int = Field(..., ge=0)
    specialists: dict[str, int] = Field(default_factory=dict)
    avg_wait_time: float = Field(default=0.0, ge=0.0, description="Temps d'attente moyen (minutes)")

    @property
    def beds_occupied(self) -> int:
        return self.beds_total - self.beds_available

    @property
    def occupancy_rate(self) -> float:
        if self.beds_total == 0:
            return 0.0
        return self.beds_occupied / self.beds_total

    @property
    def is_critical(self) -> bool:
        """True si taux d'occupation > 90% ou aucun lit disponible."""
        return self.beds_available == 0 or self.occupancy_rate >= 0.9

    def specialist_available(self, specialty: str) -> bool:
        return self.specialists.get(specialty, 0) > 0
