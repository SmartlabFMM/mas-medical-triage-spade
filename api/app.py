"""
api/app.py — Flask API with LLM Chat Integration.

New endpoint added vs original:
  POST /chat  → LLM-powered triage conversation

All original endpoints preserved:
  POST /symptoms       → ML score + decision + SHAP explanation
  POST /decision       → doctor validation
  GET  /patients       → patient list (Google Sheets)
  GET  /resources      → resource list (Google Sheets)
  GET  /metrics        → global metrics
  GET  /model-info     → ML model info
  POST /train-model    → on-demand retraining
  GET  /health         → API health
  GET  /logs           → agent log journal

Run:
  cd mas_medical_triage
  $env:PYTHONPATH = "."
  python api/app.py
"""
from __future__ import annotations

import sys
import os
import logging
import uuid
import unicodedata
from datetime import datetime

from dotenv import load_dotenv

# Ensure .env is loaded before importing modules that read env vars at import-time.
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request
from flask_cors import CORS

# ── ML engine ────────────────────────────────────────────────────────────────
try:
    from core.triage_ai import get_triage_ai
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    logging.warning(f"TriageAI unavailable: {e}")

# ── LLM engine (NEW) ─────────────────────────────────────────────────────────
try:
    from core.llm_engine import LLMEngine
    LLM_AVAILABLE = True
except ImportError as e:
    LLM_AVAILABLE = False
    LLMEngine = None
    logging.warning(f"LLMEngine unavailable: {e}")

try:
    from core.llm_engine import ConversationMemory
except ImportError:
    class ConversationMemory:
        """Minimal memory fallback used when core import fails."""

        def __init__(self):
            self._histories = {}
            self._data = {}

        def add_user(self, session_id: str, content: str) -> None:
            self._histories.setdefault(session_id, []).append({"role": "user", "content": content})

        def add_assistant(self, session_id: str, content: str) -> None:
            self._histories.setdefault(session_id, []).append({"role": "assistant", "content": content})

        def get_history(self, session_id: str):
            return self._histories.get(session_id, [])

        def update_data(self, session_id: str, data: dict) -> None:
            self._data[session_id] = data

        def get_data(self, session_id: str) -> dict:
            return self._data.get(session_id, {})

        def clear(self, session_id: str) -> None:
            self._histories.pop(session_id, None)
            self._data.pop(session_id, None)

# ── Google Sheets ────────────────────────────────────────────────────────────
try:
    from core.sheets_db import SheetsDB
    from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME
    db = SheetsDB(GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME)
    db.connect()
    SHEETS_AVAILABLE = True
    logging.info("Google Sheets connected")
except Exception as e:
    db = None
    SHEETS_AVAILABLE = False
    logging.warning(f"Google Sheets unavailable: {e}")

# ── Flask app ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("api")

app = Flask(__name__)
CORS(app, origins=["*"])

# ── LLM state (shared across requests) ──────────────────────────────────────
# Note: For multi-process deployments use Redis or a DB instead of in-memory.
if LLM_AVAILABLE:
    _llm_engine = LLMEngine(model="llama-3.1-8b-instant")
    _memory     = ConversationMemory()
else:
    _llm_engine = None
    _memory     = ConversationMemory()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def ok(data: dict, code: int = 200):
    return jsonify({"status": "ok", **data}), code

def err(message: str, code: int = 400):
    return jsonify({"status": "error", "message": message}), code

def require_json():
    if not request.is_json:
        return err("Content-Type must be application/json", 415)
    return None


def _normalize_action(raw_action: str, score: float) -> str:
    """
    Normalize any model/api action to MAS-supported actions only.
    Allowed values: hospitaliser, surveiller, transférer
    """
    txt = (raw_action or "").strip().lower()
    txt = txt.replace("-", "_").replace(" ", "_")

    # Direct accepted values
    if txt in {"hospitaliser", "surveiller", "transférer"}:
        return txt

    # Common aliases from various models/UIs
    if txt in {"transferer", "transfert", "transfer", "refer", "referer"}:
        return "transférer"
    if txt in {"watch", "monitor", "observation", "observer"}:
        return "surveiller"
    if txt in {"hospitalize", "hospitaliser_urgent", "admit", "admission"}:
        return "hospitaliser"
    if txt in {"retour_domicile", "return_home", "home", "sortie"}:
        return "surveiller"

    # Score-based fallback if unknown
    if score >= 55:
        return "hospitaliser"
    return "surveiller"


def _normalize_symptoms(symptoms: list[str]) -> list[str]:
    """
    Normalize frontend/user symptom strings (FR/EN) into model-friendly tokens.
    """
    aliases = {
        "douleur_thoracique": "chest_pain",
        "difficulte_respiratoire": "shortness_of_breath",
        "difficultes_respiratoires": "shortness_of_breath",
        "essoufflement": "shortness_of_breath",
        "fievre_elevee": "high_fever",
        "fievre": "fever",
        "perte_de_conscience": "loss_of_consciousness",
        "mal_de_tete": "headache",
        "nausee": "nausea",
        "vomissements": "vomiting",
        "trauma_cranien": "confusion",
        "hemorragie": "bleeding",
        "avc": "stroke",
        "vertiges": "dizziness",
        # Hand pain aliases
        "douleur_main": "pain_in_hand",
        "douleur_dans_la_main": "pain_in_hand",
        "mal_aux_mains": "pain_in_hand",
        "pain_in_hand": "pain_in_hand",
        "hand_pain": "pain_in_hand",
        # General pain aliases
        "douleur_articulaire": "joint_pain",
        "joint_pain": "joint_pain",
        "mal_au_dos": "back_pain",
        "douleur_dos": "back_pain",
        "mal_au_ventre": "stomach_pain",
        "douleur_abdominale": "stomach_pain",
    }
    out = []
    for s in symptoms:
        txt = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
        txt = txt.strip().lower().replace(" ", "_").replace("-", "_")
        while "__" in txt:
            txt = txt.replace("__", "_")
        out.append(aliases.get(txt, txt))
    # keep order, remove duplicates
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def _fallback_chat_result(session_id: str, message: str) -> dict:
    """
    Rule-based chat fallback so /chat still works in realtime mode without LLM.
    Completes quickly for urgent inputs to trigger MAS triage.
    """
    text = message.lower()
    history = _memory.get_history(session_id) if _memory else []
    user_turns = len([h for h in history if h.get("role") == "user"]) + 1

    symptom_hits = []
    if "chest" in text or "thorac" in text:
        symptom_hits.append("chest pain")
    if "breath" in text or "respir" in text:
        symptom_hits.append("shortness of breath")
    if "dizz" in text or "vertig" in text:
        symptom_hits.append("dizziness")
    if "fever" in text or "fiev" in text:
        symptom_hits.append("fever")
    if "stroke" in text or "avc" in text:
        symptom_hits.append("stroke signs")
    if "unconscious" in text or "inconscient" in text:
        symptom_hits.append("loss of consciousness")
    # Enhanced hand pain detection
    if "hand" in text and ("pain" in text or "douleur" in text):
        symptom_hits.append("pain in hand")
    if "broken" in text and "hand" in text:
        symptom_hits.append("pain in hand")
    if "numbness" in text and "hand" in text:
        symptom_hits.append("pain in hand")
    if "tingling" in text and "hand" in text:
        symptom_hits.append("pain in hand")
    # Enhanced headache detection
    if "headache" in text or "mal de tête" in text:
        symptom_hits.append("headache")
    if "sharp" in text and ("head" in text or "headache" in text):
        symptom_hits.append("headache")
    if "pain" in text and ("head" in text or "side" in text):
        symptom_hits.append("headache")

    pain = 0
    # Enhanced pain extraction for various pain descriptions
    pain_keywords = [
        "pain is", "douleur est", "pain level", "niveau de douleur",
        "severe pain", "douleur sévère", "intense pain", "douleur intense",
        "mild pain", "douleur légère", "moderate pain", "douleur modérée"
    ]
    
    # Check for explicit pain levels first
    for n in range(10, -1, -1):
        if f"{n}/10" in text or f"pain is {n}" in text or f"douleur {n}" in text:
            pain = n
            break
    
    # If no explicit level, check for pain keywords
    if pain == 0:
        if any(keyword in text for keyword in pain_keywords):
            # Default to medium if pain mentioned but no level specified
            pain = 5

    urgency = "medium"
    if any(s in symptom_hits for s in ["chest pain", "shortness of breath", "loss of consciousness", "stroke signs"]) or pain >= 8:
        urgency = "high"
    if ("chest pain" in symptom_hits and "shortness of breath" in symptom_hits) or "loss of consciousness" in symptom_hits:
        urgency = "critical"

    # Complete after enough data or multiple turns to feed realtime MAS pipeline.
    is_complete = bool(symptom_hits and (pain > 0 or user_turns >= 2))
    if urgency in ("high", "critical"):
        is_complete = True

    next_question = "" if is_complete else "On a scale from 0 to 10, how severe is your pain right now?"
    reply = (
        "Thank you. I have enough information and I am forwarding your case to the clinical team now."
        if is_complete
        else "I understand. To complete your triage quickly, please tell me your pain score from 0 to 10."
    )

    return {
        "reply": reply,
        "extracted_data": {
            "symptoms": list(dict.fromkeys(symptom_hits).keys()),  # Remove duplicates
            "pain_level": pain,
            "urgency": urgency,
            "is_conscious": "unconscious" not in text and "inconscient" not in text,
            "notes": "Rule-based fallback chat mode",
            "confidence": 0.45 if is_complete else 0.3,
        },
        "is_complete": is_complete,
        "next_question": next_question,
    }


# ══════════════════════════════════════════════════════════════════════════════
# POST /chat — LLM-powered triage conversation  (NEW)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/chat", methods=["POST"])
def post_chat():
    """
    LLM-powered triage dialogue endpoint.

    Input JSON:
    {
        "message":    "I have chest pain and feel dizzy",
        "session_id": "abc123"        ← optional, created if missing
    }

    Output JSON:
    {
        "status":     "ok",
        "session_id": "abc123",
        "reply":      "I'm sorry to hear that. How long have you had the chest pain?",
        "extracted_data": {
            "symptoms":     ["chest pain", "dizziness"],
            "pain_level":   7,
            "urgency":      "high",
            "is_conscious": true,
            "notes":        "Chest pain with dizziness — cardiac evaluation needed",
            "confidence":   0.65
        },
        "is_complete":   false,
        "next_question": "How long have you had the chest pain?"
    }
    """
    e = require_json()
    if e:
        return e

    body    = request.get_json()
    message = str(body.get("message", "")).strip()

    if not message:
        return err("'message' field is required.")

    # Create or reuse session
    session_id = str(body.get("session_id", "") or uuid.uuid4())

    # ── Fallback if LLM is not available ─────────────────────────────────────
    if not LLM_AVAILABLE or _llm_engine is None:
        result = _fallback_chat_result(session_id, message)
        _memory.add_user(session_id, message)
        _memory.add_assistant(session_id, result["reply"])
        _memory.update_data(session_id, result["extracted_data"])
        if result.get("is_complete") and SHEETS_AVAILABLE and db:
            try:
                extracted = result.get("extracted_data", {})
                db.upsert_patient({
                    "id": session_id,
                    "name": f"WebPatient-{session_id[:8]}",
                    "age": 35,
                    "gender": "?",
                    "symptoms": extracted.get("symptoms", []),
                    "pain_level": extracted.get("pain_level", 0),
                    "arrival_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "en_attente",
                })
                db.log(
                    agent="API/LLMChat",
                    action="chat_completed_patient_queued",
                    details=f"queued_from_chat urgency={extracted.get('urgency', 'medium')}",
                    patient_id=session_id,
                    niveau="INFO",
                )
            except Exception as exc:
                logger.warning(f"Could not queue completed chat session in Sheets: {exc}")
        return ok({
            "session_id": session_id,
            "reply": result["reply"],
            "extracted_data": result["extracted_data"],
            "is_complete": result["is_complete"],
            "next_question": result["next_question"],
        })

    # ── Get conversation history for this session ─────────────────────────────
    history = _memory.get_history(session_id)
    # History contains all previous turns; pass everything except current message
    history_so_far = history[:]   # snapshot before we add the new turn

    # ── Call LLM ─────────────────────────────────────────────────────────────
    try:
        result = _llm_engine.analyze(
            message=message,
            history=history_so_far,
        )
    except Exception as exc:
        logger.error(f"LLM error in /chat: {exc}")
        return err(f"LLM processing error: {str(exc)}", 500)

    # ── Update conversation memory ────────────────────────────────────────────
    _memory.add_user(session_id, message)
    _memory.add_assistant(session_id, result["reply"])
    _memory.update_data(session_id, result["extracted_data"])

    # In realtime mode, push completed chat sessions into Patients sheet so
    # ConversationalAgent.WatchPatientsBehaviour can trigger full triage flow.
    if result.get("is_complete") and SHEETS_AVAILABLE and db:
        try:
            extracted = result.get("extracted_data", {})
            db.upsert_patient({
                "id": session_id,
                "name": f"WebPatient-{session_id[:8]}",
                "age": 35,
                "gender": "?",
                "symptoms": extracted.get("symptoms", []),
                "pain_level": extracted.get("pain_level", 0),
                "arrival_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "en_attente",
            })
            db.log(
                agent="API/LLMChat",
                action="chat_completed_patient_queued",
                details=f"queued_from_chat urgency={extracted.get('urgency', 'medium')}",
                patient_id=session_id,
                niveau="INFO",
            )
        except Exception as exc:
            logger.warning(f"Could not queue completed chat session in Sheets: {exc}")

    # ── Log to Google Sheets ──────────────────────────────────────────────────
    if SHEETS_AVAILABLE and db:
        try:
            db.log(
                agent="API/LLMChat",
                action="chat_turn",
                details=(
                    f"session={session_id} "
                    f"urgency={result['extracted_data']['urgency']} "
                    f"confidence={result['extracted_data']['confidence']:.2f}"
                ),
                patient_id=session_id,
                niveau="INFO",
            )
        except Exception as exc:
            logger.warning(f"Sheets log failed: {exc}")

    logger.info(
        f"POST /chat | session={session_id} | "
        f"urgency={result['extracted_data']['urgency']} | "
        f"pain={result['extracted_data']['pain_level']} | "
        f"complete={result['is_complete']}"
    )

    return ok({
        "session_id":     session_id,
        "reply":          result["reply"],
        "extracted_data": result["extracted_data"],
        "is_complete":    result.get("is_complete", False),
        "next_question":  result.get("next_question", ""),
    })


# ══════════════════════════════════════════════════════════════════════════════
# GET /chat/session/<session_id> — Retrieve full conversation history  (NEW)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/chat/session/<session_id>", methods=["GET"])
def get_chat_session(session_id: str):
    """Return the full conversation history and latest extracted data."""
    if not LLM_AVAILABLE or _memory is None:
        return err("LLM engine not available", 503)

    history = _memory.get_history(session_id)
    data    = _memory.get_data(session_id)

    return ok({
        "session_id":     session_id,
        "history":        history,
        "extracted_data": data,
        "turn_count":     len(history),
    })


# ══════════════════════════════════════════════════════════════════════════════
# DELETE /chat/session/<session_id> — Clear a session  (NEW)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/chat/session/<session_id>", methods=["DELETE"])
def delete_chat_session(session_id: str):
    """Clear conversation memory for a session (e.g. patient discharged)."""
    if _memory:
        _memory.clear(session_id)
    return ok({"session_id": session_id, "cleared": True})


# ══════════════════════════════════════════════════════════════════════════════
# POST /symptoms — Full ML triage (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/symptoms", methods=["POST"])
def post_symptoms():
    """
    Analyze patient symptoms with ML model + SHAP explanation.

    Input JSON:
    {
        "name":       "Alice Martin",
        "age":        72,
        "gender":     "F",
        "symptoms":   ["chest_pain", "shortness_of_breath"],
        "pain_level": 8,
        "conscious":  true
    }
    """
    e = require_json()
    if e:
        return e

    body = request.get_json()

    symptoms = body.get("symptoms", [])
    if not symptoms or not isinstance(symptoms, list):
        return err("'symptoms' field is required and must be a list.")
    normalized_symptoms = _normalize_symptoms(symptoms)

    name       = str(body.get("name", "Unknown")).strip()
    age        = int(body.get("age", 35))
    gender     = str(body.get("gender", "?"))
    pain_level = int(body.get("pain_level", 0))
    conscious  = bool(body.get("conscious", True))
    patient_id = str(uuid.uuid4())

    if ML_AVAILABLE:
        try:
            ai = get_triage_ai()
            result = ai.predict(
                symptoms=normalized_symptoms,
                pain_level=pain_level,
                patient_id=patient_id,
                top_k=6,
            )
            score            = result["severity_score"]
            decision         = result["decision"]
            explanation      = result["explanation"]
            symptoms_found   = result["symptoms_found"]
            symptoms_unknown = result["symptoms_unknown"]
            confidence       = result["model_confidence"]
            # Force action compatibility with SPADE agents and UI.
            decision["action"] = _normalize_action(decision.get("action", ""), score)
        except Exception as exc:
            logger.error(f"ML error: {exc}")
            score, decision, explanation, symptoms_found, symptoms_unknown, confidence = \
                _rule_based_fallback(normalized_symptoms, pain_level)
    else:
        score, decision, explanation, symptoms_found, symptoms_unknown, confidence = \
            _rule_based_fallback(normalized_symptoms, pain_level)

    if SHEETS_AVAILABLE and db:
        try:
            db.upsert_patient({
                "id":             patient_id,
                "name":           name,
                "age":            age,
                "gender":         gender,
                "symptoms":       symptoms,
                "pain_level":     pain_level,
                "severity_score": score,
                # Action finale doit venir du cycle d'agents (MetaAgent),
                # pas de la pré-analyse API.
                "action":         "",
                "arrival_time":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status":         "en_attente",
            })
            db.log(
                agent="API/TriageAI",
                action="symptom_analysis",
                details=f"score={score} action={decision['action']} symptoms={len(symptoms_found)}",
                patient_id=patient_id,
                niveau="INFO",
            )
        except Exception as exc:
            logger.warning(f"Sheets write failed: {exc}")

    logger.info(f"POST /symptoms | patient={name} | score={score} | "
                f"action={decision['action']}")

    return ok({
        "patient_id":       patient_id,
        "severity_score":   score,
        "decision":         decision,
        "explanation":      explanation,
        "symptoms_found":   symptoms_found,
        "symptoms_unknown": symptoms_unknown,
        "model_confidence": confidence,
    })


# ══════════════════════════════════════════════════════════════════════════════
# POST /decision — Doctor validation (unchanged)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/decision", methods=["POST"])
def post_decision():
    e = require_json()
    if e:
        return e

    body         = request.get_json()
    patient_id   = body.get("patient_id", "")
    action       = body.get("action", "")
    score_raw    = body.get("score", None)
    score        = None
    if score_raw not in (None, ""):
        try:
            score = float(score_raw)
            score = max(0.0, min(100.0, score))
        except (TypeError, ValueError):
            return err("score must be a number when provided.")
    validated_by = body.get("validated_by", "Doctor")

    if not patient_id or not action:
        return err("patient_id and action are required.")

    if SHEETS_AVAILABLE and db:
        try:
            db.update_patient_decision(patient_id, action, score)
            db.insert_decision({
                "patient_id":     patient_id,
                "severity_score": score if score is not None else "",
                "action":         action,
                "rationale":      f"Validated by {validated_by}",
                "cycle_count":    1,
                "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "decided_by":     validated_by,
            })
            db.log("API", "decision_validated",
                   f"action={action} by={validated_by}", patient_id, "INFO")
        except Exception as exc:
            logger.warning(f"Sheets decision write failed: {exc}")

    return ok({"patient_id": patient_id,
               "action": action,
               "validated_by": validated_by})


# ══════════════════════════════════════════════════════════════════════════════
# GET endpoints (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/patients", methods=["GET"])
def get_patients():
    if not SHEETS_AVAILABLE:
        return ok({"data": _demo_patients(), "count": 3, "source": "demo"})
    try:
        data = db.get_patients()
        return ok({"data": data, "count": len(data)})
    except Exception as e:
        return err(str(e), 500)


@app.route("/resources", methods=["GET"])
def get_resources():
    if not SHEETS_AVAILABLE:
        return ok({"data": _demo_resources(), "count": 5, "source": "demo"})
    try:
        data = db.get_resources()
        return ok({"data": data, "count": len(data)})
    except Exception as e:
        return err(str(e), 500)


@app.route("/decisions", methods=["GET"])
def get_decisions():
    if not SHEETS_AVAILABLE:
        return ok({"data": [], "count": 0})
    try:
        data = db.get_decisions()
        return ok({"data": data, "count": len(data)})
    except Exception as e:
        return err(str(e), 500)


@app.route("/logs", methods=["GET"])
def get_logs():
    limit = request.args.get("limit", 50, type=int)
    if not SHEETS_AVAILABLE:
        return ok({"data": [], "count": 0})
    try:
        data = db.get_logs(limit=limit)
        return ok({"data": data, "count": len(data)})
    except Exception as e:
        return err(str(e), 500)


@app.route("/metrics", methods=["GET"])
def get_metrics():
    if not SHEETS_AVAILABLE:
        return ok({"data": {"total_patients": 0, "total_decisions": 0,
                            "available_resources": 0, "critical_patients": 0}})
    try:
        data = db.get_metrics()
        return ok({"data": data})
    except Exception as e:
        return err(str(e), 500)


@app.route("/health", methods=["GET"])
def health():
    return ok({
        "api":       "running",
        "ml":        ML_AVAILABLE,
        "llm":       LLM_AVAILABLE,
        "sheets":    SHEETS_AVAILABLE,
        "timestamp": datetime.now().isoformat(),
    })


# ══════════════════════════════════════════════════════════════════════════════
# Rule-based fallback (unchanged from original)
# ══════════════════════════════════════════════════════════════════════════════

def _rule_based_fallback(symptoms: list, pain_level: int):
    critical = {"chest_pain", "cardiac_arrest", "respiratory_failure",
                "stroke", "unconscious"}
    high     = {"shortness_of_breath", "severe_bleeding", "high_fever",
                "severe_headache"}

    s_set = {s.lower() for s in symptoms}
    score = min(100, pain_level * 8 + len(symptoms) * 5)

    if s_set & critical or pain_level >= 9:
        score   = max(score, 85)
        action  = "hospitaliser"
        urgency = "critique"
        color   = "#dc2626"
        label   = "IMMEDIATE HOSPITALIZATION"
    elif s_set & high or pain_level >= 6:
        score   = max(score, 55)
        action  = "hospitaliser"
        urgency = "urgent"
        color   = "#f97316"
        label   = "URGENT HOSPITALIZATION"
    else:
        action  = "surveiller"
        urgency = "normal"
        color   = "#22c55e"
        label   = "MONITORING"

    decision = {
        "action":       action,
        "urgency":      urgency,
        "label":        label,
        "color":        color,
        "instructions": f"Rule-based decision — score {score}",
    }
    return score, decision, [], symptoms, [], "rule-based"


def _demo_patients():
    return [
        {"patient_id": "demo-1", "name": "Demo Patient",
         "symptoms": "chest_pain", "status": "en_attente"},
    ]


def _demo_resources():
    return [
        {"nom_ressource": "Lit-01", "type": "Lit",
         "statut": "disponible", "service": "cardio"},
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask API on port {port}")
    logger.info(f"  ML engine  : {'available' if ML_AVAILABLE else 'NOT available'}")
    logger.info(f"  LLM engine : {'available' if LLM_AVAILABLE else 'NOT available (pip install openai)'}")
    logger.info(f"  Google Sheets: {'connected' if SHEETS_AVAILABLE else 'NOT connected'}")
    app.run(host="0.0.0.0", port=port, debug=False)
