"""Doctor-specific endpoints with JWT authentication (PostgreSQL only)."""
import time
import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from core.postgres_db import PGSheetsDB

doctor_bp = Blueprint('doctor', __name__)

def get_db():
    return PGSheetsDB()

# Mapping username -> full name as it appears in Patients table

SYMPTOMS_FR = {
    'chest_pain': 'douleur thoracique',
    'shortness_of_breath': 'difficulte respiratoire',
    'headache': 'mal de tete',
    'nausea': 'nausee',
    'fever': 'fievre',
    'high_fever': 'fievre elevee',
    'vomiting': 'vomissements',
    'dizziness': 'vertiges',
    'abdominal_pain': 'douleur abdominale',
    'back_pain': 'douleur dorsale',
    'sweating': 'transpiration',
    'palpitations': 'palpitations',
    'unconscious': 'inconscient',
    'bleeding': 'saignement',
    'fracture': 'fracture',
    'trauma': 'traumatisme',
    'arm_pain': 'douleur bras',
}

DOCTOR_NAMES = {
    'dr.martin': 'Dr. Martin Dubois',
    'dr.sophie': 'Dr. Sophie Laurent',
    'dr.pierre': 'Dr. Pierre Moreau',
    'dr.isabelle': 'Dr. Isabelle Bernard',
    'dr.jeanluc': 'Dr. Jean-Luc Petit',
    'dr.catherine': 'Dr. Catherine Roux',
    'dr.philippe': 'Dr. Philippe Durand',
    'dr.marie': 'Dr. Marie Lefebvre',
    'dr.ayoub': 'Dr. Ayoub',
    'dr.hassin': 'Dr. Hassin',
}

def get_patient_score(patient):
    """Extract and normalize patient severity score."""
    raw = (patient.get('severity_score') or
           patient.get('score_gravite') or
           patient.get('score_gravite'))
    if raw is None or raw == '':
        return 0
    try:
        if isinstance(raw, str):
            txt = raw.strip().lower().replace("/100", "").replace("%", "")
            txt = txt.replace(",", ".")
            value = float(txt)
        else:
            value = float(raw)
        # Heuristic for locale-mangled decimals
        while value > 100 and value < 10000:
            value /= 10.0
        return max(0, min(100, round(value, 1)))
    except (ValueError, TypeError):
        return 0

@doctor_bp.route('/patients', methods=['GET'])
@jwt_required()
def get_doctor_patients():
    """Get patients assigned to the currently authenticated doctor."""
    current_user = get_jwt_identity()
    doctor_username = current_user
    try:
        db = get_db()
        patients = db.get_patients()  # list of dicts
        doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)
        print(f"[Doctor] Looking for patients assigned to: '{doctor_full_name}' (username: {doctor_username})")
        print(f"[Doctor] Total patients in database: {len(patients)}")

        doctor_patients = []
        for p in patients:
            assigned = p.get('medecin_assigne', '')
            if assigned and assigned == doctor_full_name:
                status = str(p.get('statut', '')).strip().lower()
                # Ignore treated or transferred patients
                if not (status.startswith('trait') or status.startswith('transf')):
                    p['normalized_score'] = get_patient_score(p)
                    raw = p.get('symptomes', [])
                    if isinstance(raw, list):
                        p['symptomes'] = [SYMPTOMS_FR.get(s.lower(), s) for s in raw]
                    doctor_patients.append(p)

        print(f"[Doctor] Found {len(doctor_patients)} patients for {doctor_full_name}")

        # Sort by severity score (highest first), then by arrival time
        doctor_patients.sort(key=lambda p: (-p.get('normalized_score', 0), p.get('heure_arrivee', '')))

        # Calculate KPIs
        total_patients = len(doctor_patients)
        severity_counts = {
            'critical': sum(1 for p in doctor_patients if p['normalized_score'] >= 80),
            'urgent': sum(1 for p in doctor_patients if 60 <= p['normalized_score'] < 80),
            'moderate': sum(1 for p in doctor_patients if 40 <= p['normalized_score'] < 60),
            'low': sum(1 for p in doctor_patients if p['normalized_score'] < 40)
        }

        return jsonify({
            'success': True,
            'doctor_username': doctor_username,
            'total_patients': total_patients,
            'severity_counts': severity_counts,
            'patients': doctor_patients
        }), 200

    except Exception as e:
        print(f"[Doctor] Error getting patients: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@doctor_bp.route('/patient/<patient_id>/status', methods=['POST'])
@jwt_required()
def update_patient_status(patient_id):
    """Update the status of a patient assigned to the authenticated doctor."""
    current_user = get_jwt_identity()
    doctor_username = current_user
    try:
        data = request.get_json()
        new_status = data.get('status')
        if not new_status:
            return jsonify({'success': False, 'error': 'Le statut est requis'}), 400

        db = get_db()
        doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)

        # Verify patient belongs to this doctor
        patients = db.get_patients()
        patient_found = False
        for p in patients:
            if str(p.get('patient_id', '')) == str(patient_id):
                assigned = p.get('medecin_assigne', '')
                if assigned and assigned == doctor_full_name:
                    patient_found = True
                    patient_data = p  # Store patient data for archiving
                break

        if not patient_found:
            return jsonify({'success': False, 'error': 'Patient non trouvé ou non assigné à ce médecin'}), 404

        # Update patient status
        updates = {'statut': str(new_status).strip()}
        if str(new_status).lower().startswith('transf'):
            updates['mode_affectation'] = 'Transfert'
            updates['specialite_assignee'] = 'Externe'

        # When patient is treated or transferred, release the bed
        if new_status.lower() in ['traité', 'transféré']:
            if patient_data.get('lit_assigne'):
                updates['lit_assigne'] = None  # Clear bed assignment

        db.patient_repo.update(patient_id, updates)

        # Archive patient if status is final (traité, transféré) and not already archived
        archived = False
        final_statuses = ['traité', 'transféré']
        if new_status.lower() in final_statuses:
            try:
                # Check if already archived
                existing_archived = db.archived_repo.get_by_id(patient_id)
                if not existing_archived:
                    # Create archived record with all patient data
                    archived_record = {
                        'patient_id': patient_id,
                        'nom': patient_data.get('nom'),
                        'age': patient_data.get('age'),
                        'genre': patient_data.get('genre'),
                        'symptomes': patient_data.get('symptomes'),  # stored as-is from DB
                        'symptoms_details': patient_data.get('symptoms_details'),
                        'score_gravite': patient_data.get('score_gravite'),
                        'action_finale': patient_data.get('action_finale'),
                        'heure_arrivee': patient_data.get('heure_arrivee'),
                        'statut': new_status,
                        'specialite_assignee': patient_data.get('specialite_assignee'),
                        'medecin_assigne': patient_data.get('medecin_assigne'),
                        'lit_assigne': patient_data.get('lit_assigne'),
                        'mode_affectation': patient_data.get('mode_affectation'),
                        'archived_at': datetime.datetime.now(),
                        'archived_reason': new_status
                    }
                    db.archived_repo.create(archived_record)
                    archived = True

                    # Release bed if one was assigned and patient is archived
                    if patient_data.get('lit_assigne'):
                        bed_id = patient_data.get('lit_assigne')
                        db.resource_repo.update(bed_id, {
                            'statut': 'disponible',
                            'patient_assigne': None,
                            'disponibilite': True
                        })
                        db.patient_repo.update(patient_id, {'lit_assigne': ''})
            except Exception as archive_error:
                # Log error but don't break the status update
                print(f"[Doctor] Error archiving patient: {archive_error}")

        return jsonify({
            'success': True,
            'message': f'Status updated to "{new_status}"',
            'patient_id': patient_id,
            'new_status': new_status,
            'archived': archived
        }), 200

    except Exception as e:
        print(f"[Doctor] Error updating status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@doctor_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_doctor_stats():
    """Get statistics for the authenticated doctor's patients."""
    current_user = get_jwt_identity()
    doctor_username = current_user
    try:
        db = get_db()
        patients = db.get_patients()
        doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)

        doctor_patients = []
        for p in patients:
            assigned = p.get('medecin_assigne', '')
            if assigned and assigned == doctor_full_name:
                status_val = str(p.get('statut', '')).strip().lower()
                if not (status_val.startswith('trait') or status_val.startswith('transf')):
                    doctor_patients.append(p)

        total = len(doctor_patients)
        severity_distribution = {'critical': 0, 'urgent': 0, 'moderate': 0, 'low': 0}
        status_distribution = {}
        for p in doctor_patients:
            score = get_patient_score(p)
            if score >= 80:
                severity_distribution['critical'] += 1
            elif score >= 60:
                severity_distribution['urgent'] += 1
            elif score >= 40:
                severity_distribution['moderate'] += 1
            else:
                severity_distribution['low'] += 1
            status = p.get('statut', 'En attente')
            status_distribution[status] = status_distribution.get(status, 0) + 1

        return jsonify({
            'success': True,
            'doctor_username': doctor_username,
            'total_patients': total,
            'severity_distribution': severity_distribution,
            'status_distribution': status_distribution
        }), 200

    except Exception as e:
        print(f"[Doctor] Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@doctor_bp.route('/history', methods=['GET'])
@jwt_required()
def get_doctor_history():
    """Get archived patients for the authenticated doctor."""
    current_user = get_jwt_identity()
    doctor_username = current_user
    doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)
    try:
        from database.models import ArchivedPatient
        from database.connection import db as sql_db
        archived = sql_db.session.query(ArchivedPatient).all()
        # Filter by doctor
        doctor_history = [
            p.to_dict() for p in archived
            if str(p.medecin_assigne or '') == doctor_full_name
        ]
        # Normalize scores and translate symptoms
        for p in doctor_history:
            p['normalized_score'] = get_patient_score(p)
            raw = p.get('symptomes', [])
            if isinstance(raw, list):
                p['symptomes'] = [SYMPTOMS_FR.get(s.lower(), s) for s in raw]
        # Sort by archived_at descending
        doctor_history.sort(
            key=lambda p: str(p.get('archived_at', '') or ''),
            reverse=True
        )
        return jsonify({
            'success': True,
            'doctor_username': doctor_username,
            'total': len(doctor_history),
            'history': doctor_history
        }), 200
    except Exception as e:
        print(f"[Doctor] Error getting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500






