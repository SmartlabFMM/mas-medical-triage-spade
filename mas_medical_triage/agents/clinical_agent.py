"""
agents/clinical_agent.py — Agent Clinique SPADE + BDI (Rule-based v2.0).
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


class ClinicalAgent(Agent):
    """
    Agent BDI d'évaluation clinique.
    Utilise le calculateur de gravité basé sur les règles v2.0.
    """

    class TriageBehaviour(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            msg_type = get_msg_type(msg)
            sender = str(msg.sender) if msg.sender else "unknown"
            print(f"[DEBUG] ClinicalAgent received message from {sender}, type={msg_type}")
            
            payload  = parse_body(msg)
            pid      = get_patient_id(msg)

            if msg_type == MessageType.SYMPTOM_REPORT:
                patient_data = payload["patient"]
                # Récupérer symptoms_details du payload (envoyé séparément par ConversationalAgent)
                symptoms_details = payload.get("symptoms_details")
                if symptoms_details:
                    patient_data["symptoms_details"] = symptoms_details
                patient = Patient(**patient_data)
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
            # Nouveau calculateur v2.0 - utiliser les détails des symptômes si disponibles
            detailed_symptoms = []
            if patient.symptoms_details:
                # Parser symptoms_details (JSON string ou liste)
                try:
                    import json
                    symptoms_data = json.loads(patient.symptoms_details) if isinstance(patient.symptoms_details, str) else patient.symptoms_details
                    if isinstance(symptoms_data, list):
                        detailed_symptoms = [
                            {
                                'name': s.get('name', s.get('symptom', '')),
                                'intensity': s.get('intensity', 2),
                                'duration': s.get('duration', 'recente')
                            }
                            for s in symptoms_data
                        ]
                except:
                    pass
            
            if not detailed_symptoms:
                # Fallback avec valeurs par défaut
                detailed_symptoms = [
                    {'name': s, 'intensity': 2, 'duration': 'recente'}
                    for s in patient.symptoms
                ]
            
            result = compute_score(
                symptoms=detailed_symptoms,
                pain_level=patient.pain_level,
                age=patient.age,
                is_conscious=True
            )
            score = result['score']
            self.agent.beliefs.update("severity_score", score)
            # Stocker aussi la classification complète
            self.agent.beliefs.update("severity_result", result)
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
            
            # Classification finale selon les règles demandées:
            # 0-25: Léger → À surveiller (retour à domicile)
            # 26-50: Modéré → Hospitalisation légère OBLIGATOIRE (généraliste)
            # 51-75: Urgent → Hospitalisation obligatoire
            # 76-100: Critique → Hospitalisation prioritaire
            if score >= 76:  # Critique
                hospitalize_utility = 0.95 if beds_ok else 0.3
                watch_utility = 0.05
                transfer_utility = 0.9 if not beds_ok else 0.2
                hospitalize_rationale = f"URGENCE CRITIQUE (score {score:.1f}) - hospitalisation prioritaire immédiate"
            elif score >= 51:  # Urgent
                hospitalize_utility = 0.85 if beds_ok else 0.4
                watch_utility = 0.15
                transfer_utility = 0.7 if not beds_ok else 0.25
                hospitalize_rationale = f"URGENT (score {score:.1f}) - hospitalisation obligatoire"
            elif score >= 26:  # Modéré → Hospitalisation légère OBLIGATOIRE
                hospitalize_utility = 0.75 if beds_ok else 0.5  # Supérieur à watch pour forcer l'hospitalisation
                watch_utility = 0.25  # Réduit car hospitalisation obligatoire
                transfer_utility = 0.3 if not beds_ok else 0.1
                hospitalize_rationale = f"Modéré (score {score:.1f}) - hospitalisation légère obligatoire"
            else:  # Léger (0-25)
                hospitalize_utility = 0.15 if beds_ok else 0.05
                watch_utility = 0.85
                transfer_utility = 0.1 if not beds_ok else 0.05
                hospitalize_rationale = f"Léger (score {score:.1f}) - surveillance à domicile"

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
            # ── Calculateur basé sur les règles v2.0 ──────────
            # Le score a été calculé dans _update_beliefs et stocké dans severity_score
            score = self.agent.beliefs.get("severity_score") or 0.0
            score = max(0.0, min(100.0, round(float(score), 1)))
            log_agent_state("ClinicalAgent", f"Rule-based score={score:.1f} ({severity_label(score)})")

            # Desires → Intentions
            options = self._generate_options(ml_score=score)
            best    = self._select_intention(options)

            log_agent_state("ClinicalAgent",
                            f"score={score:.1f} ({severity_label(score)}) "
                            f"→ intention={best.action.value}")

            # Envoi au Meta-Agent (avec données patient pour assignation médecin)
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
                    "patient":        patient.model_dump(),  # Données patient pour routage
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
