"""api/app.py - Flask API for MAS medical triage system."""

from __future__ import annotations

import os
import uuid
import logging
import unicodedata
from datetime import datetime
from sqlalchemy import text
from urllib.parse import unquote

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Database imports (from root-level database package)
from database.connection import db, init_app

# Models
from database.models import (
    Patient, Decision, Resource, Log, Doctor, ArchivedPatient
)

# Flask App Setup
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv(
    'JWT_SECRET_KEY', 'your-secret-key-change-this-in-production'
)
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False

# Initialize database (once, early)
init_app(app)

# Repository layer (initialized within app context)
with app.app_context():
    from core.postgres_db import PGSheetsDB
    pg_db = PGSheetsDB()

jwt = JWTManager(app)
CORS(app, origins=["*"])

# Register Blueprints
from api.auth import auth_bp
from api.doctor import doctor_bp

app.register_blueprint(auth_bp)
print("[Auth] Blueprint registered")

app.register_blueprint(doctor_bp, url_prefix='/api/doctor')
print("[Doctor] Blueprint registered")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
)
logger = logging.getLogger('api')

# Helpers
def ok(data: dict, code: int = 200):
    return jsonify({'status': 'ok', **data}), code

def err(message: str, code: int = 400):
    return jsonify({'status': 'error', 'message': message}), code

def require_json():
    if not request.is_json:
        return err('Content-Type must be application/json', 415)
    return None

# Utility Functions
def _normalize_action(raw_action: str, score: float) -> str:
    txt = (raw_action or '').strip().lower()
    txt = txt.replace('-', '_').replace(' ', '_')
    if txt in {'hospitaliser', 'surveiller', 'transferer'}:
        return txt
    if txt in {'transferer', 'transfert', 'transfer', 'refer', 'referer'}:
        return 'transferer'
    if txt in {'watch', 'monitor', 'observation', 'observer'}:
        return 'surveiller'
    if txt in {'hospitalize', 'hospitaliser_urgent', 'admit', 'admission'}:
        return 'hospitaliser'
    if txt in {'retour_domicile', 'return_home', 'home', 'sortie'}:
        return 'surveiller'
    return 'hospitaliser' if score >= 55 else 'surveiller'

def _normalize_symptoms(symptoms: list[str]) -> list[str]:
    aliases = {
        'douleur_thoracique': 'chest_pain',
        'difficulte_respiratoire': 'shortness_of_breath',
        'difficultes_respiratoires': 'shortness_of_breath',
        'essoufflement': 'shortness_of_breath',
        'fievre_elevee': 'high_fever',
        'fievre': 'fever',
        'perte_de_conscience': 'loss_of_consciousness',
        'mal_de_tete': 'headache',
        'nausee': 'nausea',
        'vomissements': 'vomiting',
        'trauma_cranien': 'confusion',
        'hemorragie': 'bleeding',
        'avc': 'stroke',
        'vertiges': 'dizziness',
        'douleur_main': 'pain_in_hand',
        'douleur_dans_la_main': 'pain_in_hand',
        'mal_aux_mains': 'pain_in_hand',
        'pain_in_hand': 'pain_in_hand',
        'hand_pain': 'pain_in_hand',
        'douleur_articulaire': 'joint_pain',
        'joint_pain': 'joint_pain',
        'mal_au_dos': 'back_pain',
        'douleur_dos': 'back_pain',
        'mal_au_ventre': 'stomach_pain',
        'douleur_abdominale': 'stomach_pain',
    }
    out = []
    for s in symptoms:
        txt = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode('ascii')
        txt = txt.strip().lower().replace(' ', '_').replace('-', '_')
        while '__' in txt:
            txt = txt.replace('__', '_')
        out.append(aliases.get(txt, txt))
    seen = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq

def _rule_based_fallback(symptoms: list, pain_level: int):
    critical = {'chest_pain', 'cardiac_arrest', 'respiratory_failure', 'stroke', 'unconscious'}
    high = {'shortness_of_breath', 'severe_bleeding', 'high_fever', 'severe_headache'}
    s_set = {s.lower() for s in symptoms}
    score = min(100, pain_level * 8 + len(symptoms) * 5)
    if s_set & critical or pain_level >= 9:
        score = max(score, 85)
        action = 'hospitaliser'
        urgency = 'critique'
        color = '#dc2626'
        label = 'IMMEDIATE HOSPITALIZATION'
    elif s_set & high or pain_level >= 6:
        score = max(score, 55)
        action = 'hospitaliser'
        urgency = 'urgent'
        color = '#f97316'
        label = 'URGENT HOSPITALIZATION'
    else:
        action = 'surveiller'
        urgency = 'normal'
        color = '#22c55e'
        label = 'MONITORING'
    decision = {
        'action': action,
        'urgency': urgency,
        'label': label,
        'color': color,
        'instructions': f'Rule-based decision - score {score}',
    }
    return score, decision, [], symptoms, [], 'rule-based'

def _demo_patients():
    return [{'patient_id': 'demo-1', 'name': 'Demo Patient', 'symptoms': 'chest_pain', 'status': 'en_attente'}]

def _demo_resources():
    return [{'nom_ressource': 'Lit-01', 'type': 'Lit', 'statut': 'disponible', 'service': 'cardio'}]

# API Endpoints
@app.route('/symptoms', methods=['POST'])
def post_symptoms():
    e = require_json()
    if e:
        return e

    body = request.get_json()
    symptoms = body.get('symptoms', [])
    if not symptoms or not isinstance(symptoms, list):
        return err("'symptoms' field is required and must be a list.")
    normalized_symptoms = _normalize_symptoms(symptoms)

    name = str(body.get('name', 'Unknown')).strip()
    age = int(body.get('age', 35))
    gender = str(body.get('gender', '?'))
    pain_level = int(body.get('pain_level', 0))
    conscious = bool(body.get('conscious', True))
    symptoms_details = body.get('symptoms_details', '')
    patient_id = uuid.uuid4()

    print(f'[API DEBUG] Name received: {name} (body.name: {body.get("name")})')

    try:
        patient_data = {
            'patient_id': patient_id,
            'nom': name,
            'age': age,
            'genre': gender,
            'symptomes': normalized_symptoms,
            'symptoms_details': symptoms_details,
            'action_finale': '',
            'heure_arrivee': datetime.now(),
            'statut': 'en_attente',
            'specialite_assignee': '',
            'medecin_assigne': '',
            'lit_assigne': '',
            'mode_affectation': '',
        }
        pg_db.insert_patient(patient_data)

        log_data = {
            'agent': 'API',
            'action': 'patient_created',
            'details': f'symptoms={len(symptoms)} - waiting for agent triage',
            'patient_id': str(patient_id),
            'niveau': 'INFO',
        }
        pg_db.log(**log_data)
    except Exception as exc:
        logger.warning(f'DB write failed: {exc}')
        return err(f'Database error: {exc}', 500)

    logger.info(f'POST /symptoms | patient={name} | status=en_attente | waiting for agents')
    return ok({
        'patient_id': str(patient_id),
        'severity_score': None,
        'message': 'Patient enregistre - triage en cours par agents'
    })

@app.route('/decision', methods=['POST'])
def post_decision():
    e = require_json()
    if e:
        return e

    body = request.get_json()
    patient_id_str = body.get('patient_id', '')
    action = body.get('action', '')
    score_raw = body.get('score', None)
    score = None
    if score_raw not in (None, ''):
        try:
            score = float(score_raw)
            score = max(0.0, min(100.0, score))
        except (TypeError, ValueError):
            return err('score must be a number when provided.')
    validated_by = body.get('validated_by', 'Doctor')

    if not patient_id_str or not action:
        return err('patient_id and action are required.')

    try:
        patient_uuid = uuid.UUID(patient_id_str)

        # Update patient status
        pg_db.update_patient_status(patient_id_str, action)

        # Create decision record
        decision_data = {
            'patient_id': patient_uuid,
            'score_gravite': score,
            'action': action,
            'raisonnement': f'Validated by {validated_by}',
            'nb_cycles': 1,
            'timestamp': datetime.now(),
            'agent_decideur': validated_by,
        }
        pg_db.insert_decision(decision_data)

        # Log decision
        log_data = {
            'agent': 'API',
            'action': 'decision_validated',
            'details': f'action={action} by={validated_by}',
            'patient_id': patient_id_str,
            'niveau': 'INFO',
        }
        pg_db.log(**log_data)
    except Exception as exc:
        logger.warning(f'DB decision write failed: {exc}')
        return err(f'Database error: {exc}', 500)

    return ok({
        'patient_id': patient_id_str,
        'action': action,
        'validated_by': validated_by
    })

@app.route('/patients', methods=['GET'])
def get_patients():
    try:
        patients = pg_db.get_patients()
        return ok({'data': patients, 'count': len(patients)})
    except Exception as e:
        logger.warning(f'DB query failed: {e}')
        return ok({'data': _demo_patients(), 'count': 3, 'source': 'demo'})

@app.route('/resources', methods=['GET'])
def get_resources():
    try:
        resources = pg_db.get_resources()
        # Replace patient_assigne UUID with patient name for clarity
        for r in resources:
            pid = r.get('patient_assigne')
            if pid:
                patient = pg_db.patient_repo.get_by_id(pid)
                if patient:
                    r['patient_assigne'] = patient.nom
        return ok({'data': resources, 'count': len(resources)})
    except Exception as e:
        logger.warning(f'DB query failed: {e}')
        return ok({'data': _demo_resources(), 'count': 5, 'source': 'demo'})

@app.route('/decisions', methods=['GET'])
def get_decisions():
    try:
        decisions = pg_db.get_decisions()
        return ok({'data': decisions, 'count': len(decisions)})
    except Exception as e:
        return err(str(e), 500)

@app.route('/logs', methods=['GET'])
def get_logs():
    limit = request.args.get('limit', 50, type=int)
    try:
        logs = pg_db.get_logs(limit=limit)
        return ok({'data': logs, 'count': len(logs)})
    except Exception as e:
        return err(str(e), 500)

@app.route('/metrics', methods=['GET'])
def get_metrics():
    try:
        total_patients = pg_db.patient_repo.db.query(Patient).count()
        total_decisions = pg_db.decision_repo.db.query(Decision).count()
        available_resources = pg_db.resource_repo.db.query(Resource).filter(Resource.statut == 'disponible').count()
        critical_patients = pg_db.patient_repo.db.query(Patient).filter(Patient.action_finale == 'hospitaliser').count()
        return ok({
            'data': {
                'total_patients': total_patients,
                'total_decisions': total_decisions,
                'available_resources': available_resources,
                'critical_patients': critical_patients,
            }
        })
    except Exception as e:
        return err(str(e), 500)

@app.route('/health', methods=['GET'])
def health():
    try:
        with app.app_context():
            db.session.execute(text('SELECT 1'))
            db_status = 'postgresql'
    except Exception:
        db_status = 'disconnected'
    return ok({
        'api': 'running',
        'database': db_status,
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

# Admin Endpoints
@app.route('/admin/dashboard', methods=['GET'])
def admin_dashboard():
    try:
        active_patients = pg_db.patient_repo.db.query(Patient).all()
        archived_patients = pg_db.archived_repo.db.query(ArchivedPatient).all()
        patients = active_patients + archived_patients
        doctors = pg_db.doctor_repo.db.query(Doctor).all()
        resources = pg_db.resource_repo.db.query(Resource).all()

        today = datetime.now().strftime('%Y-%m-%d')
        patients_today = len([p for p in patients if today in str(p.heure_arrivee)])

        severity_distribution = {'leger': 0, 'modere': 0, 'urgent': 0, 'critique': 0}
        for p in patients:
            decision = (
                pg_db.decision_repo.db.query(Decision)
                .filter(Decision.patient_id == str(p.patient_id))
                .order_by(Decision.timestamp.desc())
                .first()
            )
            score = decision.score_gravite if decision else 0
            if isinstance(score, str):
                try:
                    score = float(score)
                except Exception:
                    score = 0
            if score <= 25:
                severity_distribution['leger'] += 1
            elif score <= 50:
                severity_distribution['modere'] += 1
            elif score <= 75:
                severity_distribution['urgent'] += 1
            else:
                severity_distribution['critique'] += 1

        total_beds = len([r for r in resources if 'lit' in str(r.nom_ressource).lower()])
        occupied_beds = len([
            r for r in resources
            if 'lit' in str(r.nom_ressource).lower()
            and r.patient_assigne is not None
            and str(r.patient_assigne).strip() != ''
        ])
        bed_occupancy_rate = (occupied_beds / total_beds * 100) if total_beds > 0 else 0
        available_beds = total_beds - occupied_beds

        doctors_by_specialty = {}
        for d in doctors:
            spec = d.specialite or 'Unknown'
            if d.disponible:
                doctors_by_specialty[spec] = doctors_by_specialty.get(spec, 0) + 1

        transfers = len([p for p in patients if p.action_finale == 'transferer'])
        hospitalized = len([p for p in patients if p.action_finale == 'hospitaliser'])
        total_patients_with_action = len([p for p in patients if p.action_finale])
        hospitalization_rate = (hospitalized / total_patients_with_action * 100) if total_patients_with_action > 0 else 0
        critical_detected = severity_distribution['critique']

        doctor_load = []
        for d in doctors:
            doctor_load.append({
                'name': d.nom,
                'specialty': d.specialite,
                'available': d.disponible,
                'patient_count': 1 if d.patient_assigne else 0,
            })

        daily_stats = {}
        for p in patients:
            date = str(p.heure_arrivee)[:10]
            if date and date != 'None':
                if date not in daily_stats:
                    daily_stats[date] = {'total': 0, 'critical': 0, 'hospitalized': 0}
                daily_stats[date]['total'] += 1
                decision = (
                    pg_db.decision_repo.db.query(Decision)
                    .filter(Decision.patient_id == str(p.patient_id))
                    .order_by(Decision.timestamp.desc())
                    .first()
                )
                score = decision.score_gravite if decision else 0
                if isinstance(score, str):
                    try:
                        score = float(score)
                    except Exception:
                        score = 0
                if score > 75:
                    daily_stats[date]['critical'] += 1
                if p.action_finale == 'hospitaliser':
                    daily_stats[date]['hospitalized'] += 1

        hourly_stats = {
            f'{h:02d}:00': {'total': 0, 'critical': 0, 'hospitalized': 0}
            for h in range(24)
        }
        for p in patients:
            arrival = str(p.heure_arrivee)
            if arrival and arrival != 'None' and arrival.startswith(today):
                try:
                    hour_key = arrival[11:13] + ':00'
                    if hour_key not in hourly_stats:
                        hourly_stats[hour_key] = {'total': 0, 'critical': 0, 'hospitalized': 0}
                    hourly_stats[hour_key]['total'] += 1
                    decision = (
                        pg_db.decision_repo.db.query(Decision)
                        .filter(Decision.patient_id == str(p.patient_id))
                        .order_by(Decision.timestamp.desc())
                        .first()
                    )
                    score = decision.score_gravite if decision else 0
                    if isinstance(score, str):
                        try:
                            score = float(score)
                        except Exception:
                            score = 0
                    if score > 75:
                        hourly_stats[hour_key]['critical'] += 1
                    if p.action_finale == 'hospitaliser':
                        hourly_stats[hour_key]['hospitalized'] += 1
                except Exception:
                    pass

        return jsonify({
            'patients_today': patients_today,
            'severity_distribution': severity_distribution,
            'bed_occupancy_rate': round(bed_occupancy_rate, 2),
            'available_beds': available_beds,
            'total_beds': total_beds,
            'doctors_available_by_specialty': doctors_by_specialty,
            'total_doctors': len(doctors),
            'transfers': transfers,
            'hospitalization_rate': round(hospitalization_rate, 2),
            'critical_detected': critical_detected,
            'doctor_load': doctor_load,
            'daily_stats': daily_stats,
            'hourly_stats': hourly_stats,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f'[Admin Dashboard] Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/resources', methods=['GET', 'POST', 'PUT'])
def admin_resources():
    try:
        if request.method == 'GET':
            resources = pg_db.get_resources()
            return jsonify(resources), 200

        elif request.method == 'POST':
            data = request.get_json()
            pg_db.upsert_resource(data)
            return jsonify({'success': True, 'message': 'Resource added'}), 201

        elif request.method == 'PUT':
            data = request.get_json()
            pg_db.upsert_resource(data)
            return jsonify({'success': True, 'message': 'Resource updated'}), 200
    except Exception as e:
        logger.error(f'[Admin Resources] Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/resources/<nom_ressource>', methods=['DELETE'])
def delete_resource(nom_ressource):
    try:
        nom_ressource = unquote(nom_ressource)
        pg_db.resource_repo.delete(nom_ressource)
        return jsonify({'success': True, 'message': 'Resource deleted'}), 200
    except Exception as e:
        logger.error(f'[Admin Delete Resource] Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/doctors', methods=['GET', 'POST', 'PUT'])
def admin_doctors():
    try:
        if request.method == 'GET':
            doctors = pg_db.get_doctors()
            return jsonify(doctors), 200

        elif request.method == 'POST':
            data = request.get_json()
            doctor_id = data.get('doctor_id')
            if not doctor_id:
                doctor_id = str(uuid.uuid4())
            data['doctor_id'] = doctor_id
            pg_db.insert_doctor(data)
            return jsonify({'success': True, 'doctor_id': doctor_id}), 201

        elif request.method == 'PUT':
            data = request.get_json()
            doctor_id = data.get('doctor_id')
            if not doctor_id:
                return jsonify({'error': 'doctor_id required'}), 400
            pg_db.doctor_repo.update(doctor_id, data)
            return jsonify({'success': True, 'message': 'Doctor updated'}), 200
    except Exception as e:
        logger.error(f'[Admin Doctors] Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/doctors/<doctor_id>', methods=['DELETE'])
def delete_doctor(doctor_id):
    try:
        pg_db.doctor_repo.delete(doctor_id)
        return jsonify({'success': True, 'message': 'Doctor deleted'}), 200
    except Exception as e:
        logger.error(f'[Admin Delete Doctor] Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/patients', methods=['GET'])
def admin_patients():
    try:
        active_patients = pg_db.patient_repo.db.query(Patient).all()
        archived_patients = pg_db.archived_repo.db.query(ArchivedPatient).all()
        all_patients = (
            [p.to_dict() for p in active_patients]
            + [p.to_dict() for p in archived_patients]
        )
        all_patients.sort(key=lambda x: str(x.get('heure_arrivee', '')), reverse=True)
        return jsonify(all_patients), 200
    except Exception as e:
        logger.error(f'[Admin Patients] Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/decisions', methods=['GET'])
def admin_decisions():
    try:
        decisions = pg_db.decision_repo.db.query(Decision).all()
        return jsonify([d.to_dict() for d in decisions]), 200
    except Exception as e:
        logger.error(f'[Admin Decisions] Error: {e}')
        return jsonify({'error': str(e)}), 500

@app.route('/admin/logs', methods=['GET'])
def admin_logs():
    try:
        logs = pg_db.log_repo.db.query(Log).order_by(Log.timestamp.desc()).limit(100).all()
        return jsonify([l.to_dict() for l in logs]), 200
    except Exception as e:
        logger.error(f'[Admin Logs] Error: {e}')
        return jsonify({'error': str(e)}), 500

# Entry Point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f'Starting Flask API on port {port}')
    try:
        with app.app_context():
            db.session.execute(text('SELECT 1'))
            connection_status = 'postgresql'
    except Exception:
        connection_status = 'disconnected'
    logger.info(f'  database: {connection_status}')
    app.run(host='0.0.0.0', port=port, debug=False)
