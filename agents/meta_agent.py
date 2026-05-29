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
from config import AGENTS_JID
from core.sheets_adapter import SheetsAdapter as SheetsDB
from core.specialty_router import route, Specialty
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

            sender = str(msg.sender) if msg.sender else "unknown"
            msg_type_str = msg_type.value if hasattr(msg_type, 'value') else str(msg_type)
            print(f"[DEBUG MetaAgent] Received {msg_type_str} from {sender} for patient {pid}")
            print(f"[DEBUG MetaAgent] Current clinical keys: {list(self.agent._clinical.keys())}")
            print(f"[DEBUG MetaAgent] Current resource keys: {list(self.agent._resource.keys())}")

            if msg_type == MessageType.CLINICAL_OPTIONS:
                self.agent._clinical[pid] = payload
                self.agent._cycles.setdefault(pid, 1)
                print(f"[DEBUG MetaAgent] Stored clinical data for {pid}")
                
                # If we don't have resource data yet, request it
                if pid not in self.agent._resource:
                    print(f"[DEBUG MetaAgent] Requesting resource status for {pid}")
                    await self._request_resources(pid)
                    
            elif msg_type in (MessageType.RESOURCE_STATUS,
                               MessageType.CRITICAL_CONSTRAINT):
                self.agent._resource[pid] = payload
                print(f"[DEBUG MetaAgent] Stored resource data for {pid}")
                # Clean up request tracking
                if pid in self.agent._resource_requests:
                    del self.agent._resource_requests[pid]
                    print(f"[DEBUG MetaAgent] Cleaned up resource request tracking for {pid}")

            await self._try_decide(pid)

        async def _try_decide(self, pid: str) -> None:
            has_clinical = pid in self.agent._clinical
            has_resource = pid in self.agent._resource
            print(f"[DEBUG MetaAgent._try_decide] pid={pid}, has_clinical={has_clinical}, has_resource={has_resource}")
            if not has_clinical or not has_resource:
                print(f"[DEBUG MetaAgent._try_decide] Cannot decide - missing data for {pid}")
                return
            print(f"[DEBUG MetaAgent._try_decide] Making decision for {pid}!")

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
            print(f"[DEBUG MetaAgent] Sent FINAL_DECISION to ConversationalAgent for {pid}")

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

            # ═════════════════════════════════════════════════════════════════
            # ASSIGNATION MÉDECIN (uniquement pour hospitalisation)
            # ═════════════════════════════════════════════════════════════════
            print(f"[MetaAgent-Doctors] DEBUG - Action={action.value}, Score={score}, Patient={pid}")
            if action == ActionType.HOSPITALIZE:
                print(f"[MetaAgent-Doctors] Lancement assignation médecin pour {pid}")
                await self._assign_doctor_to_patient(pid, clinical, score)
            elif action == ActionType.TRANSFER:
                print(f"[MetaAgent-Doctors] Transfer demandé pour {pid} — mise à jour des métadonnées patient")
                if self.agent.db:
                    self.agent.db.update_patient_doctor_assignment(
                        patient_id=pid,
                        doctor_name=None,
                        specialty="Externe",
                        mode="Transfert"
                    )
            else:
                print(f"[MetaAgent-Doctors] Pas d'assignation médecin - action n'est pas HOSPITALIZE")

            self.agent._cycles.pop(pid, None)

        async def _request_resources(self, pid: str) -> None:
            """Request current resource status from ResourceAgent with retry tracking."""
            import time
            
            # Check if we already have a pending request for this patient
            if pid in self.agent._resource_requests:
                req_info = self.agent._resource_requests[pid]
                elapsed = time.time() - req_info["timestamp"]
                
                # If request is still pending and not timed out, don't send another
                if elapsed < self.agent._resource_timeout_seconds:
                    print(f"[DEBUG MetaAgent] Resource request for {pid} already pending ({elapsed:.1f}s ago)")
                    return
                
                # Check retry limit
                if req_info["retries"] >= self.agent._resource_retry_limit:
                    print(f"[WARN MetaAgent] Max retries reached for {pid}, using degraded resource data")
                    # Use degraded/fallback resource data
                    self.agent._resource[pid] = {
                        "resource_state": {
                            "beds_total": 50,
                            "beds_available": 10,  # Assume some availability
                            "specialists": {"cardiologie": 2, "neurologie": 2, 
                                          "traumatologie": 3, "general": 4},
                            "is_critical": False,
                            "degraded_mode": True,
                        },
                        "degraded": True,
                    }
                    # Trigger decision with degraded data
                    await self._try_decide(pid)
                    return
                
                # Increment retry count
                req_info["retries"] += 1
                print(f"[DEBUG MetaAgent] Retry #{req_info['retries']} for resource request {pid}")
            else:
                # First request
                self.agent._resource_requests[pid] = {
                    "timestamp": time.time(),
                    "retries": 0,
                }
            
            msg = build_message(
                to=AGENTS_JID["resource"],
                performative=Performative.REQUEST,
                msg_type=MessageType.RESOURCE_STATUS,
                payload={"patient_id": pid, "request": "current_status"},
                patient_id=pid, thread=pid
            )
            await self.send(msg)
            print(f"[DEBUG MetaAgent] Sent resource request for {pid} (retry: {self.agent._resource_requests[pid]['retries']})")

        async def _assign_doctor_to_patient(self, pid: str, clinical: dict, score: float) -> None:
            """
            Assigne un médecin au patient selon la logique hiérarchique:
            
            Classification finale:
            - 26-50 (Modéré): Hospitalisation légère → Généraliste direct
            - 51-75 (Urgent): Hospitalisation obligatoire → Spécialiste selon symptômes
            - 76-100 (Critique): Hospitalisation prioritaire → Spécialiste prioritaire
            
            Logique:
            1. Modéré (26-50): Assigner directement à un généraliste
            2. Urgent/Critique (51+): Déterminer spécialité via specialty_router
            3. Repli sur généraliste si spécialiste non disponible
            4. File d'attente si saturation
            """
            try:
                # Modes d'affectation
                MODE_SPECIALISTE_DIRECT = "Spécialiste direct"
                MODE_GENERALISTE_REPLI = "Généraliste de repli"
                MODE_GENERALISTE_MODERE = "Hospitalisation légère (généraliste)"
                MODE_FILE_ATTENTE = "File d'attente"
                
                # Extraire les symptômes uniquement (pas de signes vitaux pour le routage)
                patient = clinical.get("patient", {})
                symptoms = patient.get("symptoms", [])
                
                print(f"[MetaAgent-Doctors] DEBUG - Score: {score}, Clinical data: {clinical.keys()}")
                print(f"[MetaAgent-Doctors] DEBUG - Patient data: {patient.keys()}")
                print(f"[MetaAgent-Doctors] DEBUG - Symptoms: {symptoms}")
                
                # Étape 1: Déterminer la spécialité requise
                # Cas Modéré (26-50): Hospitalisation légère → Généraliste direct
                if 26 <= score <= 50:
                    required_specialty = Specialty.GENERALISTE.value
                    reason = "Hospitalisation légère pour cas modéré (score 26-50)"
                    print(f"[MetaAgent-Doctors] Patient {pid} - MODÉRÉ: Assignation directe à un généraliste")
                else:
                    # Cas Urgent (51-75) ou Critique (76-100): Spécialité selon symptômes
                    routing_result = route(symptoms, {})
                    required_specialty = routing_result["specialty"]
                    reason = routing_result["reason"]
                    
                print(f"[MetaAgent-Doctors] Patient {pid} - Spécialité requise: {required_specialty} ({reason})")
                
                # Étape 2: Essayer d'affecter un spécialiste
                print(f"[MetaAgent-Doctors] Recherche {required_specialty}...")
                doctor = self.agent.db.find_available_doctor(required_specialty)
                
                if doctor:
                    print(f"[MetaAgent-Doctors] Médecin {required_specialty} trouvé: {doctor['nom']}")
                    existing_assignments = [p.strip() for p in str(doctor.get("patient_assigne", "")).split(",") if p.strip()]
                    queued = len(existing_assignments) > 0
                    
                    success = self.agent.db.assign_doctor(doctor["doctor_id"], pid)
                    print(f"[MetaAgent-Doctors] assign_doctor returned: {success}")
                    
                    if success:
                        # Déterminer le mode d'affectation
                        if queued:
                            mode = MODE_FILE_ATTENTE
                        elif 26 <= score <= 50:
                            # Cas modéré: hospitalisation légère avec généraliste
                            mode = MODE_GENERALISTE_MODERE
                        else:
                            # Cas urgent/critique: spécialiste direct
                            mode = MODE_SPECIALISTE_DIRECT
                        
                        # Mettre à jour la base de données patient
                        self.agent.db.update_patient_doctor_assignment(
                            patient_id=pid,
                            doctor_name=doctor["nom"],
                            specialty=required_specialty,
                            mode=mode
                        )
                        print(f"[MetaAgent-Doctors] [OK] Patient {pid} assigné à {doctor['nom']} ({mode})")
                        return
                
                # Étape 3: Si spécialiste non disponible, chercher un généraliste
                if required_specialty != Specialty.GENERALISTE.value:
                    print(f"[MetaAgent-Doctors] Aucun {required_specialty} disponible - Recherche généraliste...")
                    
                    generalist = self.agent.db.find_available_doctor(Specialty.GENERALISTE.value)
                    
                    if generalist:
                        print(f"[MetaAgent-Doctors] Généraliste trouvé: {generalist['nom']}")
                        
                        success = self.agent.db.assign_doctor(generalist["doctor_id"], pid)
                        
                        if success:
                            self.agent.db.update_patient_doctor_assignment(
                                patient_id=pid,
                                doctor_name=generalist["nom"],
                                specialty=Specialty.GENERALISTE.value,
                                mode=MODE_GENERALISTE_REPLI
                            )
                            print(f"[MetaAgent-Doctors] [OK] Patient {pid} assigné à {generalist['nom']} ({MODE_GENERALISTE_REPLI})")
                            return
                
                # Étape 4: Si aucun médecin disponible, placer en file d'attente
                print(f"[MetaAgent-Doctors] ⚠ Aucun médecin disponible - Patient {pid} en file d'attente")
                
                self.agent.db.update_patient_doctor_assignment(
                    patient_id=pid,
                    doctor_name=None,
                    specialty=required_specialty,
                    mode=MODE_FILE_ATTENTE
                )
                
            except Exception as e:
                print(f"[MetaAgent-Doctors] Erreur assignation médecin pour {pid}: {e}")

        def _arbitrate(self, clinical: dict, resource: dict
                       ) -> tuple[ActionType, str]:
            best        = clinical.get("best_option", {})
            action_str  = best.get("action", ActionType.WATCH.value)
            rationale   = best.get("rationale", "Décision par défaut")
            # Utilise l'état RÉEL lu depuis le Sheet
            res_state   = resource.get("resource_state", {})
            beds_avail  = res_state.get("beds_available", 0)

            if action_str == ActionType.HOSPITALIZE.value:
                if beds_avail == 0:
                    log_agent_state("MetaAgent",
                                    "conflit résolu: Aucun lit disponible → transfert")
                    metrics.conflicts_resolved += 1
                    return ActionType.TRANSFER, "Aucun lit disponible"

            try:
                return ActionType(action_str), rationale
            except ValueError:
                return ActionType.WATCH, "Action inconnue → surveillance"

    async def setup(self):
        self._clinical: dict[str, dict] = {}
        self._resource: dict[str, dict] = {}
        self._cycles:   dict[str, int]  = {}
        self._resource_requests: dict[str, dict] = {}  # Track pending resource requests with timestamps
        self._resource_retry_limit: int = 3
        self._resource_timeout_seconds: float = 15.0

        from core.sheets_adapter import SheetsAdapter as SheetsDB
        try:
            self.db = SheetsDB()
            self.db.connect()
            log_agent_state("MetaAgent", "Database connected [OK]")
        except Exception as e:
            self.db = None

        t1 = Template(); t1.set_metadata("msg_type", MessageType.CLINICAL_OPTIONS)
        t2 = Template(); t2.set_metadata("msg_type", MessageType.RESOURCE_STATUS)
        t3 = Template(); t3.set_metadata("msg_type", MessageType.CRITICAL_CONSTRAINT)
        self.add_behaviour(self.DecisionBehaviour(), t1 | t2 | t3)
        log_agent_state("MetaAgent", "started (SPADE + Sheets)")
