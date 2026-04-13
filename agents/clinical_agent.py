"""
agents/clinical_agent.py — Agent Clinique SPADE + BDI + ML.
Correction : RETURN_HOME remplacé par ActionType valide (surveiller).
"""
from __future__ import annotations
import asyncio
import logging
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template
from core.message import (build_message, parse_body, get_patient_id,
                           get_msg_type, Performative, MessageType)
from core.belief_base import BeliefBase
from models.patient import Patient
from models.clinical_option import ClinicalOption, ActionType
from models.resource_state import ResourceState
from utils.severity_calculator import compute_score, severity_label
from utils.logger import log_agent_state
from config import AGENTS_JID

logger = logging.getLogger(__name__)

# ── Import optionnel du modèle ML ─────────────────────────────────────────────
try:
    from core.triage_ai import get_triage_ai
    ML_AVAILABLE = True
    logger.info("TriageAI ML disponible")
except ImportError:
    ML_AVAILABLE = False
    logger.info("TriageAI ML non disponible — mode règles métier")


class ClinicalAgent(Agent):
    """
    Agent BDI d'évaluation clinique.
    Utilise le modèle ML si disponible, sinon les règles métier.
    """

    class TriageBehaviour(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            msg_type = get_msg_type(msg)
            payload  = parse_body(msg)
            pid      = get_patient_id(msg)

            if msg_type == MessageType.SYMPTOM_REPORT:
                patient = Patient(**payload["patient"])
                await self._evaluate(patient, pid)

            elif msg_type == MessageType.REEVALUATE:
                constraints_data = payload.get("resource_state")
                if constraints_data:
                    state = ResourceState(**constraints_data)
                    self.agent.beliefs.update("resource_constraints", state)
                patient = self.agent.beliefs.get("patient")
                if patient:
                    await self._evaluate(patient, patient.id)

        # ── BDI : Beliefs ─────────────────────────────────────────────────
        def _update_beliefs(self, patient: Patient,
                            constraints: ResourceState | None = None) -> None:
            self.agent.beliefs.update("patient", patient)
            score = compute_score(patient.symptoms, patient.pain_level, patient.age)
            self.agent.beliefs.update("severity_score", score)
            if constraints:
                self.agent.beliefs.update("resource_constraints", constraints)

        # ── BDI : Desires ─────────────────────────────────────────────────
        def _generate_options(self, ml_score: float | None = None) -> list[ClinicalOption]:
            """
            Génère au minimum 3 options cliniques avec une logique améliorée.
            Les décisions sont basées sur le score de gravité et les ressources disponibles.
            """
            score = ml_score if ml_score is not None else self.agent.beliefs.get("severity_score", 0.0)
            c: ResourceState | None = self.agent.beliefs.get("resource_constraints")
            beds_ok = True if c is None else c.beds_available > 0
            
            # Logique de décision améliorée basée sur le score
            if score >= 70:  # Critique
                hospitalize_utility = 0.9 if beds_ok else 0.2
                watch_utility = 0.1
                transfer_utility = 0.8 if not beds_ok else 0.3
                hospitalize_rationale = f"Urgence critique (score {score:.1f}) - admission immédiate requise"
            elif score >= 40:  # Sévère
                hospitalize_utility = 0.7 if beds_ok else 0.3
                watch_utility = 0.4
                transfer_utility = 0.6 if not beds_ok else 0.2
                hospitalize_rationale = f"État sévère (score {score:.1f}) - hospitalisation recommandée"
            elif score >= 20:  # Modéré
                hospitalize_utility = 0.4 if beds_ok else 0.1
                watch_utility = 0.7
                transfer_utility = 0.3 if not beds_ok else 0.1
                hospitalize_rationale = f"État modéré (score {score:.1f}) - observation prioritaire"
            else:  # Léger
                hospitalize_utility = 0.1 if beds_ok else 0.05
                watch_utility = 0.8
                transfer_utility = 0.1 if not beds_ok else 0.05
                hospitalize_rationale = f"État léger (score {score:.1f}) - surveillance suffisante"

            options = [
                ClinicalOption(
                    action=ActionType.HOSPITALIZE,
                    utility_score=round(hospitalize_utility, 3),
                    rationale=hospitalize_rationale + f" -- {'lits disponibles' if beds_ok else 'lits saturés'}",
                    urgency_level=max(1, min(5, int(score // 15) + 1)),
                ),
                ClinicalOption(
                    action=ActionType.WATCH,
                    utility_score=round(watch_utility, 3),
                    rationale=f"Observation et surveillance continue (score {score:.1f})",
                    urgency_level=2,
                ),
                ClinicalOption(
                    action=ActionType.TRANSFER,
                    utility_score=round(transfer_utility, 3),
                    rationale=f"Transfert vers autre structure si nécessaire (score {score:.1f})",
                    urgency_level=max(2, min(4, int(score // 20) + 2)),
                ),
            ]
            return sorted(options, reverse=True)

        # ── BDI : Intentions ──────────────────────────────────────────────
        def _select_intention(self, options: list[ClinicalOption]) -> ClinicalOption:
            return options[0]

        # ── Évaluation complète ───────────────────────────────────────────
        async def _evaluate(self, patient: Patient, pid: str) -> None:
            log_agent_state("ClinicalAgent", f"évaluation BDI — patient {pid}")

            # Beliefs
            self._update_beliefs(patient)
            rule_score = compute_score(patient.symptoms, patient.pain_level, patient.age)

            # Calcul du score (ML ou règles métier)
            ml_score   = None
            ml_explain = []

            if ML_AVAILABLE:
                try:
                    ai     = get_triage_ai()
                    result = ai.predict(
                        symptoms=patient.symptoms,
                        pain_level=patient.pain_level,
                        patient_id=pid,
                    )
                    ml_score   = result["severity_score"]
                    ml_explain = result.get("explanation", [])
                    self.agent.beliefs.update("severity_score", ml_score)
                    log_agent_state("ClinicalAgent",
                                    f"ML score={ml_score:.1f} ({severity_label(ml_score)})")
                except Exception as e:
                    log_agent_state("ClinicalAgent", f"ML erreur ({e}) — fallback règles")

            score = ml_score if ml_score is not None else self.agent.beliefs.get("severity_score", 0.0)
            # Hybrid guardrail for chat-extracted symptoms:
            # avoid under-estimation when ML misses some free-text symptom semantics.
            score = max(float(score), float(rule_score))
            score = max(0.0, min(100.0, round(score, 1)))

            # Desires → Intentions
            options = self._generate_options(ml_score=score)
            best    = self._select_intention(options)

            log_agent_state("ClinicalAgent",
                            f"score={score:.1f} ({severity_label(score)}) "
                            f"→ intention={best.action.value}")

            # Envoi au Meta-Agent
            msg = build_message(
                to=AGENTS_JID["meta"],
                performative=Performative.PROPOSE,
                msg_type=MessageType.CLINICAL_OPTIONS,
                payload={
                    "severity_score": score,
                    "severity_label": severity_label(score),
                    "options":        [o.model_dump() for o in options],
                    "best_option":    best.model_dump(),
                    "belief_revisions": self.agent.beliefs.revision_count(),
                    "ml_explanation": ml_explain,
                    "ml_used":        ML_AVAILABLE and ml_score is not None,
                },
                patient_id=pid,
                thread=pid,
            )
            await self.send(msg)

    async def setup(self):
        self.beliefs = BeliefBase()
        log_agent_state("ClinicalAgent", "started (SPADE)")

        t1 = Template(); t1.set_metadata("msg_type", MessageType.SYMPTOM_REPORT)
        t2 = Template(); t2.set_metadata("msg_type", MessageType.REEVALUATE)
        self.add_behaviour(self.TriageBehaviour(), t1 | t2)
