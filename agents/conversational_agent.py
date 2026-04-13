"""
agents/conversational_agent.py - ConversationalAgent with LLM Integration.

Changes vs original:
  - Added LLMEngine for intelligent dialogue (core/llm_engine.py)
  - Added ConversationMemory: per-patient chat history
  - Added LLMDialogueBehaviour: handles /chat endpoint messages via SPADE
  - SendSymptomsBehaviour now enriches patient data with LLM-extracted fields
  - WatchPatientsBehaviour unchanged (still polls Google Sheets every 10s)
  - ListenDecisionBehaviour unchanged
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
from core.llm_engine import LLMEngine, ConversationMemory
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
            if msg_type == MessageType.FINAL_DECISION:
                payload = parse_body(msg)
                pid = get_patient_id(msg)
                log_agent_state(
                    "ConversationalAgent",
                    f"final decision received for patient {pid}: {payload}"
                )

    # Behaviour 2 : Send symptom report to ClinicalAgent
    class SendSymptomsBehaviour(OneShotBehaviour):
        def __init__(self, patient: Patient, llm_data: dict | None = None):
            super().__init__()
            self.patient = patient
            self.llm_data = llm_data or {}   # extracted_data from LLM if available

        async def run(self):
            p = self.patient
            loop = asyncio.get_event_loop()

            # Merge LLM-extracted data into patient if available
            if self.llm_data:
                llm_symptoms = self.llm_data.get("symptoms", [])
                if llm_symptoms:
                    # Merge without duplicates
                    merged = list({s.lower() for s in p.symptoms + llm_symptoms})
                    p.symptoms = merged
                if self.llm_data.get("pain_level", 0) > 0 and p.pain_level == 0:
                    p.pain_level = self.llm_data["pain_level"]

            # Write patient to Google Sheets
            if self.agent.db:
                await loop.run_in_executor(
                    None,
                    self.agent.db.add_patient,
                    {
                        "patient_id": p.id,
                        "name": p.name,
                        "age": p.age,
                        "genre": p.gender,
                        "symptomes": ", ".join(p.symptoms),
                        "douleur": p.pain_level,
                        "arrival_time": p.arrival_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "en_attente",
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
                    "llm_data": self.llm_data,   # pass LLM context forward
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
                new_patients = [
                    p for p in patients
                    if p.get("status") == "en_attente"
                    and p.get("patient_id") not in self.agent._processed_ids
                ]

                # Trigger triage for each new patient
                new_count = 0
                for p_data in new_patients:
                    pid = p_data.get("patient_id", "")
                    if not pid:
                        continue

                    self.agent._processed_ids.add(pid)

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

                        patient = Patient(
                            id         = pid,
                            name       = p_data.get("name", f"Patient-{pid[:8]}"),
                            age        = age,
                            gender     = gender,
                            symptoms   = symptoms,
                            pain_level = pain_level,
                        )
                        b = ConversationalAgent.SendSymptomsBehaviour(patient)
                        self.agent.add_behaviour(b)
                        new_count += 1

                    except Exception as e:
                        log_agent_state("ConversationalAgent",
                                        f"Error building patient {pid}: {e}")
                        self.agent._processed_ids.discard(pid)

                if new_count > 0:
                    log_agent_state("ConversationalAgent",
                                    f"{new_count} new patient(s) sent to agents")

            except Exception as e:
                log_agent_state("ConversationalAgent",
                                f"WatchPatients error: {e}")
            
            # Sleep for the period before next check
            await asyncio.sleep(self.period)

    # Behaviour 4 : LLMDialogueBehaviour - handles /chat endpoint messages
    class LLMDialogueBehaviour(CyclicBehaviour):
        """
        Processes chat messages from the /chat Flask endpoint.
        Uses LLMEngine + ConversationMemory to maintain context.
        """

        async def run(self):
            try:
                # Non-blocking check for a pending chat request
                item = self.agent.chat_queue.get_nowait()
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.05)
                return

            session_id = item["session_id"]
            message    = item["message"]
            future     = item["future"]

            try:
                # 1. Add user turn to memory
                self.agent.memory.add_user(session_id, message)

                # 2. Get full conversation history for context
                history = self.agent.memory.get_history(session_id)
                # Exclude the message we just added (LLM receives it separately)
                history_without_last = history[:-1]

                # 3. Call LLM
                loop   = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self.agent.llm.analyze,
                    message,
                    history_without_last,
                )

                # 4. Store assistant reply in memory
                self.agent.memory.add_assistant(session_id, result["reply"])

                # 5. Update latest extracted data for this session
                self.agent.memory.update_data(session_id, result["extracted_data"])

                # 6. If assessment is complete, trigger SPADE triage pipeline
                if result.get("is_complete") and not self.agent._triggered.get(session_id):
                    self.agent._triggered[session_id] = True
                    await self._trigger_triage(session_id, result["extracted_data"])

                # 7. Resolve the future with the full response
                if not future.done():
                    future.set_result({
                        "reply":          result["reply"],
                        "extracted_data": result["extracted_data"],
                        "is_complete":    result.get("is_complete", False),
                        "next_question":  result.get("next_question", ""),
                        "session_id":     session_id,
                    })

                log_agent_state(
                    "ConversationalAgent",
                    f"LLM dialogue - session={session_id} "
                    f"urgency={result['extracted_data']['urgency']} "
                    f"confidence={result['extracted_data']['confidence']:.2f}"
                )

            except Exception as e:
                logger.error(f"LLMDialogueBehaviour error: {e}")
                if not future.done():
                    future.set_exception(e)

        async def _trigger_triage(self, session_id: str, extracted: dict) -> None:
            """
            When the LLM marks a conversation as complete, create a Patient
            and send it through the full SPADE triage pipeline.
            """
            try:
                patient = Patient(
                    id       = session_id,
                    name     = f"WebPatient-{session_id[:8]}",
                    age      = 35,
                    gender   = "autre",
                    symptoms = extracted.get("symptoms", ["unknown"]),
                    pain_level = extracted.get("pain_level", 0),
                )
                self.agent._processed_ids.add(session_id)
                b = ConversationalAgent.SendSymptomsBehaviour(
                    patient, llm_data=extracted
                )
                self.agent.add_behaviour(b)
                log_agent_state(
                    "ConversationalAgent",
                    f"Triage pipeline triggered for session {session_id}"
                )
            except Exception as e:
                logger.error(f"Error triggering triage for {session_id}: {e}")

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

        # LLM engine - configured for Groq
        self.llm    = LLMEngine(model="llama-3.1-8b-instant")
        self.memory = ConversationMemory()

        # Async queue for /chat endpoint requests
        self.chat_queue: asyncio.Queue = asyncio.Queue()

        # Tracking sets / dicts
        self._processed_ids: set[str]   = set()
        self._triggered:     dict[str, bool] = {}

        # Pre-load existing patients so they are not re-processed
        if self.db:
            try:
                existing = self.db.get_patients()
                for p in existing:
                    pid = p.get("patient_id", "")
                    if pid:
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

        # LLM dialogue loop (processes /chat queue)
        self.add_behaviour(self.LLMDialogueBehaviour())

        # Watch Google Sheets every 10 seconds
        watch_behaviour = self.WatchPatientsBehaviour()
        watch_behaviour.period = 10  # Set period manually if supported
        self.add_behaviour(watch_behaviour)

        log_agent_state("ConversationalAgent",
                        "started (SPADE + LLM + Sheets)")

    # Public API - called by simulation main.py
    async def intake_patient(self, patient: Patient) -> None:
        """Manually trigger the triage cycle for a patient (simulation mode)."""
        self._processed_ids.add(patient.id)
        b = self.SendSymptomsBehaviour(patient)
        self.add_behaviour(b)
        await b.join()

    async def chat(self, session_id: str, message: str) -> dict:
        """
        Public chat API - used by Flask /chat endpoint.
        Returns a future that will be resolved when LLM responds.
        """
        future = asyncio.Future()
        await self.chat_queue.put({
            "session_id": session_id,
            "message": message,
            "future": future,
        })
        return await future
