"""
core/message.py — Ontologie des messages FIPA-ACL pour SPADE.
"""
from __future__ import annotations
import json
from enum import Enum
from datetime import datetime
from spade.message import Message as SPADEMessage


class Performative(str, Enum):
    INFORM    = "INFORM"
    REQUEST   = "REQUEST"
    PROPOSE   = "PROPOSE"
    AGREE     = "AGREE"
    REFUSE    = "REFUSE"
    FAILURE   = "FAILURE"


class MessageType(str, Enum):
    SYMPTOM_REPORT      = "symptom_report"
    CLINICAL_OPTIONS    = "clinical_options"
    RESOURCE_STATUS     = "resource_status"
    CRITICAL_CONSTRAINT = "critical_constraint"
    FINAL_DECISION      = "final_decision"
    REEVALUATE          = "reevaluate"
    AGENT_READY         = "agent_ready"


def build_message(
    to: str,
    performative: Performative,
    msg_type: MessageType,
    payload: dict,
    patient_id: str | None = None,
    thread: str | None = None,
) -> SPADEMessage:
    msg = SPADEMessage(to=to)
    msg.set_metadata("performative", performative.value)
    msg.set_metadata("msg_type", msg_type.value)
    msg.set_metadata("timestamp", datetime.now().isoformat())
    if patient_id:
        msg.set_metadata("patient_id", patient_id)
    if thread:
        msg.thread = thread
    msg.body = json.dumps(payload, default=str)
    return msg


def parse_body(msg: SPADEMessage) -> dict:
    try:
        return json.loads(msg.body)
    except (json.JSONDecodeError, TypeError):
        return {}


def get_patient_id(msg: SPADEMessage) -> str | None:
    return msg.get_metadata("patient_id")


def get_msg_type(msg: SPADEMessage) -> str | None:
    return msg.get_metadata("msg_type")
