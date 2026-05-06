"""
api/app.py — Flask API pour système de triage médical MAS.

Endpoints:
  POST /symptoms       → Analyse symptômes + scoring agent
  POST /decision       → Validation médecin
  GET  /patients       → Liste patients (Google Sheets)
  GET  /resources      → Liste ressources (Google Sheets)
  GET  /metrics        → Métriques globales
  GET  /health         → Santé API
  GET  /logs           → Journal agent

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
from flask_jwt_extended import JWTManager

# Import auth blueprint
from api.auth import auth_bp, init_users_sheet

# ── JWT Configuration ──────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # Tokens don't expire for simplicity
jwt = JWTManager(app)
CORS(app, origins=["*"])

# ── No ML/LLM engine — Rule-based only ─────────────────────────────────────────

# ── Register Auth Blueprint ─────────────────────────────────────────────────
from api.auth import auth_bp, init_users_sheet
app.register_blueprint(auth_bp)
init_users_sheet()
print("[Auth] Blueprint registered")

# ── Register Doctor Blueprint ─────────────────────────────────────────────────
from api.doctor import doctor_bp
app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
print("[Doctor] Blueprint registered")

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


# ── No LLM state ─────────────────────────────────────────────────────────────


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

    # Common aliases from various sources
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


# ── No chat/LLM functions ────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS API
# ══════════════════════════════════════════════════════════════════════════════


# ══════════════════════════════════════════════════════════════════════════════
# POST /symptoms — Patient registration and agent triage
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/symptoms", methods=["POST"])
def post_symptoms():
    """
    Register patient symptoms and initiate agent-based triage.

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

    name             = str(body.get("name", "Unknown")).strip()
    age              = int(body.get("age", 35))
    gender           = str(body.get("gender", "?"))
    pain_level       = int(body.get("pain_level", 0))
    conscious        = bool(body.get("conscious", True))
    symptoms_details = body.get("symptoms_details", "")  # Détails JSON des symptômes
    patient_id       = str(uuid.uuid4())

    # DEBUG: Log pour vérifier le nom reçu
    print(f"[API DEBUG] Nom reçu: '{name}' (body.name: {body.get('name')})")

    # Pas de calcul de score ici - les agents SPADE calculeront le score
    # avec les multiplicateurs d'intensité et durée

    if SHEETS_AVAILABLE and db:
        try:
            db.upsert_patient({
                "id":               patient_id,
                "name":             name,
                "age":              age,
                "gender":           gender,
                "symptoms":         symptoms,
                "symptoms_details": symptoms_details,  # Stockage des détails JSON
                "pain_level":       pain_level,
                "severity_score":   "",  # Laissé vide - agents SPADE calculeront
                "action":           "",
                "arrival_time":     datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status":           "en_attente",
            })
            db.log(
                agent="API",
                action="patient_created",
                details=f"symptoms={len(symptoms)} - waiting for agent triage",
                patient_id=patient_id,
                niveau="INFO",
            )
        except Exception as exc:
            logger.warning(f"Sheets write failed: {exc}")

    logger.info(f"POST /symptoms | patient={name} | status=en_attente | waiting for agents")

    return ok({
        "patient_id":       patient_id,
        "severity_score":   None,  # Calculé par agents SPADE
        "message":          "Patient enregistré - triage en cours par agents",
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
# Admin Endpoints (Espace Agent Administratif)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    """Dashboard KPIs pour l'administrateur."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        # Récupérer toutes les données
        active_patients = db.get_patients()
        archived_patients = db.get_archived_patients()
        patients = active_patients + archived_patients
        
        doctors = db.get_doctors()
        resources = db.get_resources()
        decisions = db._sheets["Decisions"].get_all_records()

        # KPIs Calculations
        today = datetime.now().strftime("%Y-%m-%d")

        # 1. Nombre total de patients par jour
        patients_today = len([p for p in patients if today in str(p.get("heure_arrivée", ""))])

        # 2. Répartition par gravité
        severity_distribution = {"léger": 0, "modéré": 0, "urgent": 0, "critique": 0}
        for p in patients:
            score = p.get("score_gravité", 0) or 0
            if isinstance(score, str):
                try:
                    score = float(score)
                except:
                    score = 0
            if score <= 25:
                severity_distribution["léger"] += 1
            elif score <= 50:
                severity_distribution["modéré"] += 1
            elif score <= 75:
                severity_distribution["urgent"] += 1
            else:
                severity_distribution["critique"] += 1

        # 3. Taux d'occupation des lits
        total_beds = len([r for r in resources if "lit" in str(r.get("nom_ressource", "")).lower()])
        occupied_beds = len([r for r in resources if "lit" in str(r.get("nom_ressource", "")).lower() and str(r.get("patient_assigne", "")) != ""])
        bed_occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

        # 4. Lits disponibles
        available_beds = total_beds - occupied_beds

        # 5. Médecins disponibles par spécialité
        doctors_by_specialty = {}
        for d in doctors:
            spec = d.get("specialite", "Unknown")
            if str(d.get("disponible", "")).lower() == "true":
                doctors_by_specialty[spec] = doctors_by_specialty.get(spec, 0) + 1

        # 6. Nombre de transferts
        transfers = len([p for p in patients if p.get("action_finale") == "transferer"])

        # 7. Taux moyen d'hospitalisation
        hospitalized = len([p for p in patients if p.get("action_finale") == "hospitaliser"])
        total_patients = len([p for p in patients if p.get("action_finale")])
        hospitalization_rate = (hospitalized / total_patients * 100) if total_patients > 0 else 0

        # 8. Cas critiques détectés
        critical_detected = severity_distribution["critique"]

        # 9. Charge médicale par médecin
        doctor_load = []
        for d in doctors:
            doctor_load.append({
                "name": d.get("nom"),
                "specialty": d.get("specialite"),
                "available": str(d.get("disponible", "")).lower() == "true",
                "patient_count": 1 if d.get("patient_assigne") else 0
            })

        # 10. Évolution temporelle (30 derniers jours)
        daily_stats = {}
        for p in patients:
            date = str(p.get("heure_arrivée", ""))[:10]
            if date and date != "None":
                if date not in daily_stats:
                    daily_stats[date] = {"total": 0, "critical": 0, "hospitalized": 0}
                daily_stats[date]["total"] += 1
                score = p.get("score_gravité", 0) or 0
                if isinstance(score, str):
                    try:
                        score = float(score)
                    except:
                        score = 0
                if score > 75:
                    daily_stats[date]["critical"] += 1
                if p.get("action_finale") == "hospitaliser":
                    daily_stats[date]["hospitalized"] += 1

        # 11. Évolution horaire du jour courant (00h–23h)
        hourly_stats = {f"{h:02d}:00": {"total": 0, "critical": 0, "hospitalized": 0} for h in range(24)}
        for p in patients:
            arrival = str(p.get("heure_arrivée", ""))
            if arrival and arrival != "None" and arrival.startswith(today):
                # Extract hour from "YYYY-MM-DD HH:MM:SS"
                try:
                    hour_key = arrival[11:13] + ":00"
                    if hour_key not in hourly_stats:
                        hourly_stats[hour_key] = {"total": 0, "critical": 0, "hospitalized": 0}
                    hourly_stats[hour_key]["total"] += 1
                    score = p.get("score_gravité", 0) or 0
                    if isinstance(score, str):
                        try:
                            score = float(score)
                        except:
                            score = 0
                    if score > 75:
                        hourly_stats[hour_key]["critical"] += 1
                    if p.get("action_finale") == "hospitaliser":
                        hourly_stats[hour_key]["hospitalized"] += 1
                except Exception:
                    pass

        return jsonify({
            "patients_today": patients_today,
            "severity_distribution": severity_distribution,
            "bed_occupancy_rate": round(bed_occupancy_rate, 2),
            "available_beds": available_beds,
            "total_beds": total_beds,
            "doctors_available_by_specialty": doctors_by_specialty,
            "total_doctors": len(doctors),
            "transfers": transfers,
            "hospitalization_rate": round(hospitalization_rate, 2),
            "critical_detected": critical_detected,
            "doctor_load": doctor_load,
            "daily_stats": daily_stats,
            "hourly_stats": hourly_stats,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"[Admin Dashboard] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/resources", methods=["GET", "POST", "PUT"])
def admin_resources():
    """CRUD operations for resources (beds)."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        if request.method == "GET":
            resources = db.get_resources()
            return jsonify(resources), 200

        elif request.method == "POST":
            data = request.get_json()
            # Add new resource (bed)
            db._sheets["Resources"].append_row([
                data.get("nom_ressource"),
                "True",   # disponibilite
                "0",      # charge_%
                "",       # patient_assigne
                "disponible",  # statut
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # derniere_maj
            ])
            return jsonify({"success": True, "message": "Resource added"}), 201

        elif request.method == "PUT":
            data = request.get_json()
            # Update resource status
            resources = db._sheets["Resources"].get_all_records()
            for i, r in enumerate(resources, start=2):
                if r.get("nom_ressource") == data.get("nom_ressource"):
                    db._sheets["Resources"].update_cell(i, 3, data.get("statut"))  # statut
                    db._sheets["Resources"].update_cell(i, 4, data.get("patient_assigne", ""))  # patient
                    db._sheets["Resources"].update_cell(i, 6, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # derniere_maj
                    return jsonify({"success": True, "message": "Resource updated"}), 200
            return jsonify({"error": "Ressource non trouvée"}), 404

    except Exception as e:
        logger.error(f"[Admin Resources] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/resources/<nom_ressource>", methods=["DELETE"])
def delete_resource(nom_ressource):
    """Delete a resource (bed)."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        # URL decode the resource name
        from urllib.parse import unquote
        nom_ressource = unquote(nom_ressource)

        resources = db._sheets["Resources"].get_all_records()
        for i, r in enumerate(resources, start=2):
            if r.get("nom_ressource") == nom_ressource:
                db._sheets["Resources"].delete_rows(i)
                return jsonify({"success": True, "message": "Resource deleted"}), 200
        return jsonify({"error": "Ressource non trouvée"}), 404

    except Exception as e:
        logger.error(f"[Admin Delete Resource] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/doctors", methods=["GET", "POST", "PUT"])
def admin_doctors():
    """CRUD operations for doctors."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        if request.method == "GET":
            doctors = db.get_doctors()
            return jsonify(doctors), 200

        elif request.method == "POST":
            data = request.get_json()
            # Add new doctor
            doctor_id = data.get("doctor_id", f"DOC{datetime.now().strftime('%H%M%S')}")
            db._sheets["Doctors"].append_row([
                doctor_id,
                data.get("nom"),
                data.get("specialite"),
                "TRUE",
                "",
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ])
            return jsonify({"success": True, "doctor_id": doctor_id}), 201

        elif request.method == "PUT":
            data = request.get_json()
            # Update doctor
            doctors = db._sheets["Doctors"].get_all_records()
            for i, d in enumerate(doctors, start=2):
                if d.get("doctor_id") == data.get("doctor_id"):
                    if "nom" in data:
                        db._sheets["Doctors"].update_cell(i, 2, data["nom"])
                    if "specialite" in data:
                        db._sheets["Doctors"].update_cell(i, 3, data["specialite"])
                    if "disponible" in data:
                        db._sheets["Doctors"].update_cell(i, 4, "TRUE" if data["disponible"] else "FALSE")
                    db._sheets["Doctors"].update_cell(i, 6, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    return jsonify({"success": True, "message": "Doctor updated"}), 200
            return jsonify({"error": "Médecin non trouvé"}), 404

    except Exception as e:
        logger.error(f"[Admin Doctors] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/doctors/<doctor_id>", methods=["DELETE"])
def delete_doctor(doctor_id):
    """Delete a doctor."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        doctors = db._sheets["Doctors"].get_all_records()
        for i, d in enumerate(doctors, start=2):
            if d.get("doctor_id") == doctor_id:
                db._sheets["Doctors"].delete_rows(i)
                return jsonify({"success": True, "message": "Doctor deleted"}), 200
        return jsonify({"error": "Médecin non trouvé"}), 404

    except Exception as e:
        logger.error(f"[Admin Delete Doctor] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/patients", methods=["GET"])
def admin_patients():
    """Get all patients (active + archived) for admin view."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        active_patients = db.get_patients()
        archived_patients = db.get_archived_patients()
        
        # Combine both lists
        all_patients = active_patients + archived_patients
        
        # Sort by arrival time descending (most recent first)
        all_patients.sort(key=lambda x: str(x.get("heure_arrivée", "")), reverse=True)
        
        return jsonify(all_patients), 200

    except Exception as e:
        logger.error(f"[Admin Patients] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/decisions", methods=["GET"])
def admin_decisions():
    """Get all decisions for admin view."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        decisions = db._sheets["Decisions"].get_all_records()
        return jsonify(decisions), 200

    except Exception as e:
        logger.error(f"[Admin Decisions] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/logs", methods=["GET"])
def admin_logs():
    """Get system logs."""
    try:
        if not SHEETS_AVAILABLE or not db:
            return jsonify({"error": "Google Sheets non disponible"}), 503

        logs = db._sheets["Logs"].get_all_records()
        # Return last 100 logs
        return jsonify(logs[-100:] if len(logs) > 100 else logs), 200

    except Exception as e:
        logger.error(f"[Admin Logs] Error: {e}")
        return jsonify({"error": str(e)}), 500


# ══════════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting Flask API on port {port}")
    logger.info(f"  Google Sheets: {'connected' if SHEETS_AVAILABLE else 'NOT connected'}")
    app.run(host="0.0.0.0", port=port, debug=False)
