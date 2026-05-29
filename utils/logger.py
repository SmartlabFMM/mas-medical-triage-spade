"""
utils/logger.py — Journalisation centralisée (ENF-FIAB-03).
Toutes les décisions, messages et états agents sont tracés.
"""
from __future__ import annotations
import os
import sys
from loguru import logger
from config import LOG_LEVEL, LOG_FILE

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Configuration loguru
logger.remove()
logger.add(
    LOG_FILE,
    level=LOG_LEVEL,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name} | {message}",
    rotation="10 MB",
    retention="7 days",
    encoding="utf-8",
)
logger.add(
    lambda msg: sys.stdout.write(str(msg)),
    level=LOG_LEVEL,
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
)


def log_decision(decision) -> None:
    """Journalise une décision finale de triage."""
    logger.info(f"[DECISION] {decision.to_report()}")


def log_message(sender: str, receiver: str, msg_type: str, payload: str = "") -> None:
    """Journalise un message inter-agents."""
    logger.debug(f"[MSG] {sender} → {receiver} | type={msg_type} | {payload}")


def log_agent_state(agent_id: str, state: str) -> None:
    """Journalise le changement d'état d'un agent."""
    logger.info(f"[AGENT] {agent_id} | état={state}")


def log_warning(msg: str) -> None:
    logger.warning(f"[WARN] {msg}")


def log_error(msg: str) -> None:
    logger.error(f"[ERROR] {msg}")
