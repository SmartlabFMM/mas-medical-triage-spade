"""
agents/conversational_agent.py - ConversationalAgent for MAS Triage.

Behaviours:
  - WatchPatientsBehaviour: polls Google Sheets for new patients every 10s
  - SendSymptomsBehaviour: sends patient data to ClinicalAgent
  - ListenDecisionBehaviour: receives final decisions from MetaAgent
"""
from __future__ import annotations

import asyncio
import logging
import unicodedata
from datetime import datetime
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.template import Template

from core.message import (
    build_message, parse_body, get_patient_id,
    get_msg_type, Performative, MessageType,
)
from models.patient import Patient
from config import AGENTS_JID, GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME
from utils.logger import log_agent_state

logger = logging.getLogger(__name__)


class ConversationalAgent(Agent):

    # Behaviour 1 : Listen for final decisions from MetaAgent (unchanged)
    class ListenDecisionBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            msg_type = get_msg_type(msg)
            sender = str(msg.sender) if msg.sender else "unknown"
            msg_type_str = msg_type.value if hasattr(msg_type, 'value') else str(msg_type)
            print(f"[DEBUG ListenDecision] Received message from {sender}, type={msg_type_str}")
            
            if msg_type == MessageType.FINAL_DECISION:
                payload = parse_body(msg)
                pid = get_patient_id(msg)
                print(f"[DEBUG ListenDecision] FINAL DECISION for {pid}: {payload}")
                log_agent_state(
                    "ConversationalAgent",
                    f"final decision received for patient {pid}: {payload}"
                )
                
                # Write decision to Google Sheets so frontend can see it
                if self.agent.db and payload:
                    try:
                        decision_data = payload.get("decision", {})
                        action = decision_data.get("action", "")
                        score = decision_data.get("severity_score", 0)
                        print(f"[DEBUG ListenDecision] Writing to Sheets: action={action}, score={score}")
                        loop = asyncio.get_event_loop()
                        # Utiliser 'trié' (ou l'action) comme statut final pour sortir de la boucle en_attente
                        final_status = "trié"
                        await loop.run_in_executor(
                            None,
                            self.agent.db.update_patient_decision,
                            pid,
                            action,
                            float(score) if score is not None else None,
                            final_status
                        )
                        print(f"[DEBUG ListenDecision] Decision written to Google Sheets with status {final_status}!")
                    except Exception as e:
                        print(f"[ERROR ListenDecision] Failed to write decision: {e}")

    # Behaviour 2 : Send symptom report to ClinicalAgent
    class SendSymptomsBehaviour(OneShotBehaviour):
        def __init__(self, patient: Patient):
            super().__init__()
            self.patient = patient

        async def run(self):
            p = self.patient
            print(f"[DEBUG SendSymptoms] STARTING for patient {p.id}")
            loop = asyncio.get_event_loop()

            # Write patient to Google Sheets
            if self.agent.db:
                await loop.run_in_executor(
                    None,
                    self.agent.db.upsert_patient,
                    {
                        "id": p.id,
                        "name": p.name,
                        "age": p.age,
                        "gender": p.gender,
                        "symptoms": p.symptoms,
                        "symptoms_details": p.symptoms_details,
                        "pain_level": p.pain_level,
                        "arrival_time": p.arrival_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "statut": "en_cours",
                    },
                )

            # Send to ClinicalAgent
            msg = build_message(
                to=AGENTS_JID["clinical"],
                performative=Performative.INFORM,
                msg_type=MessageType.SYMPTOM_REPORT,
                payload={
                    "patient": p.model_dump(),
                    "missing_fields": [],
                    "symptoms_details": p.symptoms_details,  # Détails des symptômes (intensité, durée)
                },
                patient_id=p.id,
            )
            await self.send(msg)
            
            log_agent_state(
                "ConversationalAgent",
                f"symptom report sent - patient {p.id}"
            )

    # Behaviour 3 : Watch Google Sheets for new patients (unchanged)
    class WatchPatientsBehaviour(CyclicBehaviour):
        def __init__(self):
            super().__init__()
            self.period = 10  # Check every 10 seconds

        async def run(self):
            try:
                if not self.agent.db:
                    await asyncio.sleep(self.period)
                    return

                # Poll Google Sheets
                patients = await asyncio.get_event_loop().run_in_executor(
                    None, self.agent.db.get_patients
                )

                # Filter new patients (status = "en_attente")
                # Note: Google Sheets uses "statut" (French) not "status" (English)

                
                new_patients = [
                    p for p in patients
                    if (p.get("statut") == "en_attente" or p.get("status") == "en_attente")
                    and p.get("patient_id") not in self.agent._processed_ids
                ]

                # DEBUG: Log patient detection (only when changes or every 60s)
                total_patients = len(patients)
                en_attente_count = sum(1 for p in patients if p.get("statut") == "en_attente" or p.get("status") == "en_attente")
                processed_count = len(self.agent._processed_ids)
                
                print(f"[DEBUG] en_attente_count={en_attente_count}, new_patients={len(new_patients)}, processed={processed_count}")
                
                if len(new_patients) > 0 or not hasattr(self, '_log_counter') or self._log_counter >= 6:
                    self._log_counter = 0
                    if len(new_patients) > 0:
                        print(f"[DEBUG WatchPatients] NEW patients found: {len(new_patients)}")
                        for p in new_patients:
                            print(f"[DEBUG WatchPatients]   - {p.get('patient_id')}")
                    else:
                        print(f"[DEBUG WatchPatients] Total={total_patients}, en_attente={en_attente_count}, processed={processed_count}")
                else:
                    self._log_counter = getattr(self, '_log_counter', 0) + 1

                # Trigger triage for each new patient
                new_count = 0
                for p_data in new_patients:
                    pid = p_data.get("patient_id", "")
                    if not pid:
                        continue

                    self.agent._processed_ids.add(pid)

                    # ── Mark as "en_cours" in Sheet immediately ──────────────────
                    # This prevents re-processing if the agent restarts or if another
                    # poll happens before MetaAgent finishes.
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.agent.db.update_patient_fields, pid, {"statut": "en_cours"}
                    )

                    # Build Patient object from row data
                    try:
                        raw_symptoms = (p_data.get("symptomes") or
                                        p_data.get("symptoms") or "")
                        if isinstance(raw_symptoms, str):
                            symptoms = []
                            for s in raw_symptoms.split(","):
                                token = str(s).strip()
                                if token:
                                    # normalize display strings coming from Sheets
                                    token = unicodedata.normalize("NFKD", token).encode("ascii", "ignore").decode("ascii")
                                    symptoms.append(token)
                        elif isinstance(raw_symptoms, list):
                            symptoms = [str(s).strip() for s in raw_symptoms if str(s).strip()]
                        else:
                            symptoms = ["fatigue"]

                        if not symptoms:
                            symptoms = ["fatigue"]

                        raw_age = p_data.get("age")
                        try:
                            age = int(float(raw_age)) if raw_age not in (None, "") else 35
                        except (ValueError, TypeError):
                            age = 35
                        age = max(0, min(age, 120))

                        raw_gender = p_data.get("genre") or p_data.get("gender") or "M"
                        g = str(raw_gender).strip().lower()
                        if g in {"m", "male", "masculin"}:
                            gender = "M"
                        elif g in {"f", "female", "feminin", "feminin", "féminin"}:
                            gender = "F"
                        else:
                            gender = "autre"

                        raw_pain = p_data.get("douleur")
                        if raw_pain in (None, ""):
                            raw_pain = p_data.get("pain_level")
                        try:
                            pain_level = int(float(raw_pain)) if raw_pain not in (None, "") else 3
                        except (ValueError, TypeError):
                            pain_level = 3
                        pain_level = max(0, min(pain_level, 10))

                        # Récupérer symptoms_details depuis Google Sheets
                        symptoms_details = p_data.get("symptoms_details")
                        
                        # S'assurer que symptoms_details est une chaîne JSON
                        if isinstance(symptoms_details, list):
                            import json
                            symptoms_details = json.dumps(symptoms_details)
                        elif symptoms_details is None:
                            symptoms_details = ""
                        
                        patient = Patient(
                            id         = pid,
                            name       = p_data.get("nom") or p_data.get("name") or f"Patient-{pid[:8]}",
                            age        = age,
                            gender     = gender,
                            symptoms   = symptoms,
                            symptoms_details = symptoms_details,
                            pain_level = pain_level,
                        )
                        b = ConversationalAgent.SendSymptomsBehaviour(patient)
                        self.agent.add_behaviour(b)
                        new_count += 1

                    except Exception as e:
                        log_agent_state("ConversationalAgent",
                                        f"Error processing patient {pid}: {e}")
                        # On ne discard pas le pid ici pour éviter de boucler indéfiniment sur une erreur fatale
                        # Sauf si c'est une erreur de quota (mais l'executor aura déjà retenté)

                if new_count > 0:
                    log_agent_state("ConversationalAgent",
                                    f"{new_count} new patient(s) sent to agents")

            except Exception as e:
                log_agent_state("ConversationalAgent",
                                f"WatchPatients error: {e}")
            
            # Sleep for the period before next check
            await asyncio.sleep(self.period)


    # Setup
    async def setup(self):
        # Google Sheets connection
        from core.sheets_db import SheetsDB
        try:
            self.db = SheetsDB(
                credentials_path=GOOGLE_CREDENTIALS_PATH,
                spreadsheet_name=GOOGLE_SPREADSHEET_NAME,
            )
            self.db.connect()
            log_agent_state("ConversationalAgent", "Google Sheets connected")
        except Exception as e:
            log_agent_state("ConversationalAgent",
                            f"Sheets unavailable: {e}")
            self.db = None

        # Tracking sets
        self._processed_ids: set[str] = set()

        # Pre-load existing patients so they are not re-processed
        if self.db:
            try:
                existing = self.db.get_patients()
                for p in existing:
                    pid = p.get("patient_id", "")
                    # Only skip patients that are already processed (not "en_attente")
                    status = p.get("statut") or p.get("status") or ""
                    if pid and status != "en_attente":
                        self._processed_ids.add(pid)
                log_agent_state(
                    "ConversationalAgent",
                    f"{len(self._processed_ids)} existing patients skipped"
                )
            except Exception:
                pass

        # Behaviours
        tmpl_decision = Template()
        tmpl_decision.set_metadata("msg_type", MessageType.FINAL_DECISION)
        self.add_behaviour(self.ListenDecisionBehaviour(), tmpl_decision)

        # Watch Google Sheets every 10 seconds
        watch_behaviour = self.WatchPatientsBehaviour()
        self.add_behaviour(watch_behaviour)

        log_agent_state("ConversationalAgent",
                        "started (SPADE + Sheets)")

    # Public API - called by simulation main.py
    async def intake_patient(self, patient: Patient) -> None:
        """Manually trigger the triage cycle for a patient (simulation mode)."""
        self._processed_ids.add(patient.id)
        b = self.SendSymptomsBehaviour(patient)
        self.add_behaviour(b)
        await b.join()

