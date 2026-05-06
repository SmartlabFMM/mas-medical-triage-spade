"""
simulation/simulator.py — Simulateur de triage médical.
Orchestre les scénarios et mesure les métriques (ENF-PERF-01/02).
"""
from __future__ import annotations
import asyncio
import time
from models.patient import Patient
from agents.conversational_agent import ConversationalAgent
# Environment remplac� par SPADE
from utils.logger import log_agent_state
from utils.metrics import metrics
from config import TRIAGE_TIMEOUT


class Simulator:
    """
    Lance un ou plusieurs patients dans le système MAS
    et mesure les performances.
    """

    def __init__(self, env: Environment, conv_agent: ConversationalAgent) -> None:
        self.env        = env
        self.conv_agent = conv_agent

    async def run_patient(self, patient: Patient) -> None:
        """Lance le cycle de triage complet pour un patient."""
        metrics.total_patients += 1
        start = time.perf_counter()
        log_agent_state("Simulator", f"démarrage triage → {patient.summary()}")

        await self.conv_agent.intake_patient(patient)

        # Attente passive de la décision (timeout ENF-PERF-01)
        await asyncio.sleep(TRIAGE_TIMEOUT)

        elapsed = time.perf_counter() - start
        metrics.record_cycle(elapsed)

    async def run_scenario(self, patients: list[Patient]) -> None:
        """Lance un scénario avec plusieurs patients (ENF-PERF-02)."""
        tasks = [self.run_patient(p) for p in patients]
        await asyncio.gather(*tasks)

    def print_report(self) -> None:
        print(metrics.summary())
