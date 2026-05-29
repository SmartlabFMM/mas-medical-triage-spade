"""
main.py — Point d'entrée SPADE 4.x du système MAS de tri médical.
"""
from __future__ import annotations
import asyncio
import argparse
import json
import os
import sys
import time
import spade
from agents.conversational_agent import ConversationalAgent
from agents.clinical_agent import ClinicalAgent
from agents.resource_agent import ResourceAgent
from agents.meta_agent import MetaAgent
from models.patient import Patient
from simulation.patient_generator import generate_batch
from utils.helpers import uuid_gen
from utils.metrics import metrics
from config import AGENTS_JID, AGENTS_PWD, TRIAGE_TIMEOUT, XMPP_VERIFY_SECURITY, XMPP_ALLOW_TLS


def configure_console_encoding() -> None:
    """Force UTF-8 console output to avoid Windows cp1252 crashes."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def load_scenario(name: str) -> list[Patient]:
    path = f"simulation/scenarios/scenario_{name}.json"
    if not os.path.exists(path):
        raise FileNotFoundError(f"Scenario '{name}' introuvable : {path}")
    with open(path) as f:
        data = json.load(f)
    return [Patient(id=uuid_gen(), **p) for p in data]


async def main(scenario: str = "default", random_n: int = 0, realtime: bool = False) -> None:
    print("\n" + "="*55)
    print("  AI Multi-Agent Medical Triage System - SPADE 4")
    print("="*55 + "\n")

    conv = ConversationalAgent(
        AGENTS_JID["conversational"],
        AGENTS_PWD["conversational"],
        verify_security=XMPP_VERIFY_SECURITY
    )
    clin = ClinicalAgent(
        AGENTS_JID["clinical"],
        AGENTS_PWD["clinical"],
        verify_security=XMPP_VERIFY_SECURITY
    )
    res = ResourceAgent(
        AGENTS_JID["resource"],
        AGENTS_PWD["resource"],
        verify_security=XMPP_VERIFY_SECURITY
    )
    meta = MetaAgent(
        AGENTS_JID["meta"],
        AGENTS_PWD["meta"],
        verify_security=XMPP_VERIFY_SECURITY
    )

    print("  Demarrage des agents SPADE...")
    await meta.start(auto_register=True)
    await res.start(auto_register=True)
    await clin.start(auto_register=True)
    await conv.start(auto_register=True)

    await asyncio.sleep(2.0)
    print("  Tous les agents sont connectes.\n")

    patients = []
    if not realtime:
        if random_n > 0:
            patients = generate_batch(random_n)
            print(f"  Mode : {random_n} patients aleatoires\n")
        else:
            patients = load_scenario(scenario)
            print(f"  Scenario : {scenario} - {len(patients)} patients\n")

    metrics.total_patients = len(patients)

    # --- Mode Real-Time ---
    if realtime:
        print("  >>> MODE TEMPS RÉEL ACTIF <<<")
        print("  Les agents écoutent les nouveaux patients (Google Sheets)...")
        print("  Press Ctrl+C to stop gracefully...")
        
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            print("\n  Signal d'arrêt reçu. Arrêt en cours...")
            shutdown_event.set()
        
        try:
            while not shutdown_event.is_set():
                try:
                    await asyncio.wait_for(asyncio.sleep(1), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                except KeyboardInterrupt:
                    signal_handler()
                    break
        except Exception as e:
            print(f"  Erreur inattendue: {e}")
        finally:
            print("  Arrêt du système...")
    
    # --- Mode Simulation ---
    else:
        for patient in patients:
            print(f"  -> Triage : {patient.summary()}")
            start = time.perf_counter()
            await conv.intake_patient(patient)
            await asyncio.sleep(TRIAGE_TIMEOUT)
            metrics.record_cycle(time.perf_counter() - start)

    await conv.stop()
    await clin.stop()
    await res.stop()
    await meta.stop()

    print(metrics.summary())


if __name__ == "__main__":
    configure_console_encoding()
    parser = argparse.ArgumentParser(description="MAS Medical Triage SPADE 4")
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--random", type=int, default=0, metavar="N")
    parser.add_argument("--realtime", action="store_true", help="Mode temps réel (écoute Sheets)")
    args = parser.parse_args()
    
    # Default scenario if nothing specified
    if not args.scenario and args.random == 0 and not args.realtime:
        args.scenario = "default"
        
    spade.run(main(scenario=args.scenario, random_n=args.random, realtime=args.realtime))