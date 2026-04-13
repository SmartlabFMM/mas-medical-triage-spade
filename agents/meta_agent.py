"""
agents/meta_agent.py — MetaAgent SPADE + notification ResourceAgent pour allocation.
"""
from __future__ import annotations
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.template import Template
from core.message import (build_message, parse_body, get_patient_id,
                           get_msg_type, Performative, MessageType)
from models.triage_decision import TriageDecision
from models.clinical_option import ActionType
from utils.logger import log_agent_state, log_decision
from utils.metrics import metrics
from config import AGENTS_JID, GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME
import asyncio


class MetaAgent(Agent):

    class DecisionBehaviour(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=10)
            if not msg:
                return

            msg_type = get_msg_type(msg)
            payload  = parse_body(msg)
            pid      = get_patient_id(msg)

            if msg_type == MessageType.CLINICAL_OPTIONS:
                self.agent._clinical[pid] = payload
                self.agent._cycles.setdefault(pid, 1)
            elif msg_type in (MessageType.RESOURCE_STATUS,
                               MessageType.CRITICAL_CONSTRAINT):
                self.agent._resource[pid] = payload

            await self._try_decide(pid)

        async def _try_decide(self, pid: str) -> None:
            if pid not in self.agent._clinical or pid not in self.agent._resource:
                return

            clinical = self.agent._clinical[pid]
            resource = self.agent._resource[pid]
            cycles   = self.agent._cycles.get(pid, 1)
            score    = clinical.get("severity_score", 0.0)

            if score == 0.0 and cycles < 3:
                self.agent._cycles[pid] = cycles + 1
                metrics.reevaluations += 1
                reeval = build_message(
                    to=AGENTS_JID["clinical"],
                    performative=Performative.REQUEST,
                    msg_type=MessageType.REEVALUATE,
                    payload={"resource_state": resource.get("resource_state", {})},
                    patient_id=pid, thread=pid)
                await self.send(reeval)
                return

            # ── Finalisation (on retire des dictionnaires d'attente) ───────────
            self.agent._clinical.pop(pid)
            self.agent._resource.pop(pid)

            # Arbitrage avec l'état RÉEL du Sheet
            action, rationale = self._arbitrate(clinical, resource)

            decision = TriageDecision(
                patient_id=pid, severity_score=score,
                action=action, rationale=rationale, cycle_count=cycles)
            log_decision(decision)

            loop = asyncio.get_event_loop()

            # ── Écriture décision dans Google Sheets ──────────────────────────
            if self.agent.db:
                try:
                    await loop.run_in_executor(
                        None, self.agent.db.insert_decision,
                        decision.model_dump(mode="json"))
                    await loop.run_in_executor(
                        None, self.agent.db.update_patient_decision,
                        pid, action.value, score, "en_attente_validation")
                    await loop.run_in_executor(
                        None, self.agent.db.log,
                        "MetaAgent", "final_decision",
                        f"action={action.value} score={score:.1f}",
                        pid, "INFO")
                except Exception as e:
                    log_agent_state("MetaAgent", f"Sheets error: {e}")

            # ── Notifie ConversationalAgent ───────────────────────────────────
            notif = build_message(
                to=AGENTS_JID["conversational"],
                performative=Performative.AGREE,
                msg_type=MessageType.FINAL_DECISION,
                payload={"decision": decision.model_dump(mode="json")},
                patient_id=pid, thread=pid)
            await self.send(notif)

            # ── Notifie ResourceAgent pour ALLOUER la ressource ──────────────
            alloc = build_message(
                to=AGENTS_JID["resource"],
                performative=Performative.INFORM,
                msg_type=MessageType.FINAL_DECISION,
                payload={
                    "decision":     decision.model_dump(mode="json"),
                    "patient_name": pid[:8],
                },
                patient_id=pid, thread=pid)
            await self.send(alloc)

            self.agent._cycles.pop(pid, None)

        def _arbitrate(self, clinical: dict, resource: dict
                       ) -> tuple[ActionType, str]:
            best        = clinical.get("best_option", {})
            action_str  = best.get("action", ActionType.WATCH.value)
            rationale   = best.get("rationale", "Décision par défaut")
            # Utilise l'état RÉEL lu depuis le Sheet
            res_state   = resource.get("resource_state", {})
            beds_avail  = res_state.get("beds_available", 0)

            if action_str == ActionType.HOSPITALIZE.value and beds_avail == 0:
                log_agent_state("MetaAgent",
                                "conflit résolu: 0 lit dans Sheet → transfert")
                metrics.conflicts_resolved += 1
                return ActionType.TRANSFER, "0 lit disponible dans Sheet → transfert"

            try:
                return ActionType(action_str), rationale
            except ValueError:
                return ActionType.WATCH, "Action inconnue → surveillance"

    async def setup(self):
        self._clinical: dict[str, dict] = {}
        self._resource: dict[str, dict] = {}
        self._cycles:   dict[str, int]  = {}

        from core.sheets_db import SheetsDB
        try:
            self.db = SheetsDB(GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME)
            self.db.connect()
            log_agent_state("MetaAgent", "Google Sheets connecté ✓")
        except Exception as e:
            self.db = None

        t1 = Template(); t1.set_metadata("msg_type", MessageType.CLINICAL_OPTIONS)
        t2 = Template(); t2.set_metadata("msg_type", MessageType.RESOURCE_STATUS)
        t3 = Template(); t3.set_metadata("msg_type", MessageType.CRITICAL_CONSTRAINT)
        self.add_behaviour(self.DecisionBehaviour(), t1 | t2 | t3)
        log_agent_state("MetaAgent", "started (SPADE + Sheets)")
