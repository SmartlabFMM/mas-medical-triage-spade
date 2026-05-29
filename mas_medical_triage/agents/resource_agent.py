"""
agents/resource_agent.py — ResourceAgent SPADE.
Lit le Sheet Resources comme source de vérité et alloue/libère les ressources.
"""
from __future__ import annotations
import asyncio
import logging
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.template import Template
from core.message import (build_message, parse_body, get_patient_id,
                           get_msg_type, Performative, MessageType)
from config import (AGENTS_JID, GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME)
from utils.logger import log_agent_state, log_warning

logger = logging.getLogger(__name__)

# Mapping action → type de ressource à allouer
ACTION_RESOURCE_MAP = {
    "hospitaliser": ("Lit", "cardio"),
    "transférer":   ("Lit", "general"),
    "surveiller":   (None, None),
}


class ResourceAgent(Agent):

    # ══════════════════════════════════════════════════════════════════════════
    # Behaviour 1 : Écoute symptômes ET requêtes ressources → répond MetaAgent
    # ══════════════════════════════════════════════════════════════════════════
    class CheckResourcesBehaviour(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=5)
            if not msg:
                return

            pid     = get_patient_id(msg) or ""
            payload = parse_body(msg)
            msg_type = get_msg_type(msg)
            loop    = asyncio.get_event_loop()

            log_agent_state("ResourceAgent",
                            f"Réception {msg_type.value if hasattr(msg_type, 'value') else msg_type} pour patient {pid}")
            
            # Handle both SYMPTOM_REPORT and direct RESOURCE_STATUS queries
            await self._send_resource_status(pid, loop)
        
        async def _send_resource_status(self, pid: str, loop) -> None:
            """Send current resource status to MetaAgent with internal caching."""
            import time
            print(f"[DEBUG ResourceAgent] Sending resource status for {pid}")

            if not self.agent.db:
                log_warning("SheetsDB non connecté - ResourceAgent utilise mode dégradé")
                # Send degraded response to MetaAgent
                degraded_reply = build_message(
                    to=AGENTS_JID["meta"],
                    performative=Performative.FAILURE,
                    msg_type=MessageType.RESOURCE_STATUS,
                    payload={
                        "error": "Google Sheets connection failed",
                        "resource_state": {
                            "beds_total": 0,
                            "beds_available": 0,
                            "specialists": {
                                "cardiologie": 0,
                                "neurologie": 0,
                                "traumatologie": 0,
                                "general": 0
                            },
                            "degraded_mode": True
                        }
                    },
                    patient_id=pid,
                    thread=pid,
                )
                await self.send(degraded_reply)
                return

            # ── Utilisation d'un cache interne pour éviter de saturer l'API ──
            now = time.time()
            if (hasattr(self.agent, "_summary_cache") and 
                (now - self.agent._summary_cache_time) < 5.0):
                summary = self.agent._summary_cache
                print(f"[DEBUG ResourceAgent] Using cached summary (age: {now - self.agent._summary_cache_time:.1f}s)")
            else:
                try:
                    summary = await loop.run_in_executor(
                        None, self.agent.db.get_availability_summary)
                    self.agent._summary_cache = summary
                    self.agent._summary_cache_time = now
                except Exception as e:
                    log_warning(f"Erreur lors de la lecture des ressources : {e}")
                    # Utiliser le cache même s'il est expiré si la lecture échoue
                    if hasattr(self.agent, "_summary_cache"):
                        summary = self.agent._summary_cache
                    else:
                        return # Impossible de continuer sans données

            is_critical = summary["lits"]["disponibles"] == 0
            beds_avail  = summary["lits"]["disponibles"]
            beds_total  = summary["lits"]["total"]

            log_agent_state("ResourceAgent",
                            f"lits={beds_avail}/{beds_total} "
                            f"cardio={summary['cardio']['disponibles']} "
                            f"neuro={summary['neuro']['disponibles']}")

            # ── Log dans Sheet (limité) ───────────────────────────────────────
            if now - getattr(self.agent, "_last_log_time", 0) > 30:
                self.agent._last_log_time = now
                await loop.run_in_executor(
                    None, self.agent.db.log,
                    "ResourceAgent", "check_resources",
                    f"lits={beds_avail}/{beds_total} | "
                    f"cardio={summary['cardio']['disponibles']} | "
                    f"neuro={summary['neuro']['disponibles']}",
                    pid, "INFO",
                )

            # ── Alerte si critique ────────────────────────────────────────────
            if is_critical:
                log_warning(f"CRITIQUE — 0 lit disponible sur {beds_total}")
                await loop.run_in_executor(
                    None, self.agent.db.log,
                    "ResourceAgent", "critical_alert",
                    f"0 lit disponible sur {beds_total}",
                    pid, "WARNING",
                )
                crit = build_message(
                    to=AGENTS_JID["meta"],
                    performative=Performative.INFORM,
                    msg_type=MessageType.CRITICAL_CONSTRAINT,
                    payload={"summary": summary, "beds_available": 0},
                    patient_id=pid, thread=pid,
                )
                await self.send(crit)

            # ── Réponse au MetaAgent avec l'état RÉEL du Sheet ────────────────
            reply = build_message(
                to=AGENTS_JID["meta"],
                performative=Performative.INFORM,
                msg_type=MessageType.RESOURCE_STATUS,
                payload={
                    "resource_state": {
                        "beds_total":     beds_total,
                        "beds_available": beds_avail,
                        "specialists":    {
                            "cardiologie":   summary["cardio"]["disponibles"],
                            "neurologie":    summary["neuro"]["disponibles"],
                            "traumatologie": summary["trauma"]["disponibles"],
                            "general":       summary["general"]["disponibles"],
                        },
                        "avg_wait_time":  12.5,
                        "occupancy_rate": (
                            (beds_total - beds_avail) / beds_total
                            if beds_total > 0 else 0
                        ),
                        "is_critical":    is_critical,
                    },
                    "summary":        summary,
                    "estimated_wait": round(12.5 * (1 + (beds_total - beds_avail)
                                    / max(beds_total, 1)), 1),
                    "is_critical":    is_critical,
                },
                patient_id=pid, thread=pid,
            )
            await self.send(reply)

    # ══════════════════════════════════════════════════════════════════════════
    # Behaviour 2 : Écoute décisions finales → alloue la ressource
    # ══════════════════════════════════════════════════════════════════════════
    class AllocateResourceBehaviour(CyclicBehaviour):

        async def run(self):
            msg = await self.receive(timeout=5)
            if not msg:
                return

            pid      = get_patient_id(msg) or ""
            payload  = parse_body(msg)
            decision = payload.get("decision", {})
            action   = decision.get("action", "surveiller")
            patient_name = payload.get("patient_name", pid[:8])
            loop     = asyncio.get_event_loop()

            log_agent_state("ResourceAgent",
                            f"allocation ressource — action={action} — patient {pid}")

            # ── Détermine quelle ressource allouer selon la décision ──────────
            if action == "hospitaliser":
                success = await self._allocate(loop, pid, patient_name,
                                               "Lit", "cardio", action)
                if not success:
                    # Hospitalisation impossible sans lit → transfert obligatoire
                    log_warning(f"Aucun lit disponible pour {patient_name} - TRANSFERT FORCÉ")
                    await loop.run_in_executor(
                        None, self.agent.db.log,
                        "ResourceAgent", "transfert_forcé",
                        f"Pas de lit disponible - patient {patient_name} transféré",
                        pid, "WARNING",
                    )
                    # Mettre à jour la décision en "transférer"
                    await loop.run_in_executor(
                        None, self.agent.db.update_patient_decision,
                        pid, "transférer", "Pas de lit disponible"
                    )

            elif action == "transférer":
                # Transfère → libère une place future, log seulement
                await loop.run_in_executor(
                    None, self.agent.db.log,
                    "ResourceAgent", "transfert",
                    f"patient {patient_name} transféré — ressource non allouée",
                    pid, "INFO",
                )

            elif action == "surveiller":
                # Surveillance → pas d'allocation de lit, juste log
                await loop.run_in_executor(
                    None, self.agent.db.log,
                    "ResourceAgent", "no_allocation",
                    f"Surveillance à domicile - pas de lit nécessaire",
                    pid, "INFO",
                )

        async def _allocate(self, loop, pid: str, patient_name: str,
                             resource_type: str, specialist_type: str | None,
                             action: str) -> bool:
            """Alloue un lit et optionnellement un spécialiste. Retourne True si succès."""

            # Cherche un lit disponible dans le Sheet
            lit = await loop.run_in_executor(
                None, self.agent.db.find_available_resource, resource_type)

            if lit:
                resource_name = lit["nom_ressource"]
                success = await loop.run_in_executor(
                    None, self.agent.db.allocate_resource,
                    resource_name, pid, patient_name,
                )
                if success:
                    log_agent_state("ResourceAgent",
                                    f"{resource_name} alloué à {patient_name}")
                    await loop.run_in_executor(
                        None, self.agent.db.log,
                        "ResourceAgent", "allocation",
                        f"{resource_name} → {patient_name} ({action})",
                        pid, "INFO",
                    )
                    # Mettre à jour le lit assigné dans la fiche patient
                    await loop.run_in_executor(
                        None, self.agent.db.update_patient_bed,
                        pid, resource_name
                    )
                    # Sauvegarde pour libération future
                    self.agent._allocations[pid] = resource_name
                    return True
                else:
                    log_warning(f"Lit déjà occupé au moment de l'allocation")
                    return False
            else:
                log_warning(f"Aucun {resource_type} disponible pour {patient_name}")
                await loop.run_in_executor(
                    None, self.agent.db.log,
                    "ResourceAgent", "no_resource",
                    f"Aucun {resource_type} disponible",
                    pid, "WARNING",
                )
                return False

            # Alloue aussi un spécialiste si nécessaire
            if specialist_type:
                spec = await loop.run_in_executor(
                    None, self.agent.db.find_available_resource, specialist_type)
                if spec:
                    await loop.run_in_executor(
                        None, self.agent.db.allocate_resource,
                        spec["nom_ressource"], pid, patient_name,
                    )
                    log_agent_state("ResourceAgent",
                                    f"{spec['nom_ressource']} alloué à {patient_name}")

    # ══════════════════════════════════════════════════════════════════════════
    # Setup SPADE
    # ══════════════════════════════════════════════════════════════════════════
    async def setup(self):
        self._allocations: dict[str, str] = {}  # pid → ressource allouée

        # Connexion Google Sheets
        from core.sheets_db import SheetsDB
        try:
            self.db = SheetsDB(GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME)
            self.db.connect()
            log_agent_state("ResourceAgent", "Google Sheets connecté [OK]")
        except Exception as e:
            log_warning(f"Sheets non disponible : {e}")
            self.db = None

        # Behaviour 1 : écoute arrivée patients
        # Behaviour 1 : écoute symptômes ET requêtes ressources
        t1 = Template()
        t1.set_metadata("msg_type", MessageType.SYMPTOM_REPORT)
        t2 = Template()
        t2.set_metadata("msg_type", MessageType.RESOURCE_STATUS)
        self.add_behaviour(self.CheckResourcesBehaviour(), t1 | t2)

        # Behaviour 2 : écoute décisions finales pour allouer
        t3 = Template()
        t3.set_metadata("msg_type", MessageType.FINAL_DECISION)
        self.add_behaviour(self.AllocateResourceBehaviour(), t3)

        log_agent_state("ResourceAgent", "started (SPADE + Sheets source de vérité)")
