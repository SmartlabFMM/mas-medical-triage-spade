"""Doctor-specific endpoints with JWT authentication."""
import time
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from core.sheets_db import SheetsDB
from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME

# Create blueprint for doctor routes
doctor_bp = Blueprint('doctor', __name__)

# Simple in-memory cache to avoid hitting Google Sheets quota
_cache = {}
_cache_timestamp = 0
CACHE_DURATION = 30  # Cache data for 30 seconds

def get_db():
    """Get a connected SheetsDB instance."""
    db = SheetsDB(GOOGLE_CREDENTIALS_PATH, GOOGLE_SPREADSHEET_NAME)
    db.connect()
    return db


def invalidate_cache():
    """Invalidate cached patients data after mutations."""
    global _cache_timestamp
    _cache_timestamp = 0

# Mapping username -> full name as it appears in Patients sheet
DOCTOR_NAMES = {
    'dr.martin': 'Dr. Martin Dubois',
    'dr.sophie': 'Dr. Sophie Laurent',
    'dr.pierre': 'Dr. Pierre Moreau',
    'dr.isabelle': 'Dr. Isabelle Bernard',
    'dr.jeanluc': 'Dr. Jean-Luc Petit',
    'dr.catherine': 'Dr. Catherine Roux',
    'dr.philippe': 'Dr. Philippe Durand',
    'dr.marie': 'Dr. Marie Lefebvre',
    'dr.ayoub': 'Dr.Ayoub',
    'dr.hassin': 'Dr.Hassin',
}

def get_patients_cached():
    """Get patients with caching to reduce Google Sheets API calls."""
    global _cache, _cache_timestamp
    current_time = time.time()
    
    # Return cached data if still valid
    if 'patients' in _cache and (current_time - _cache_timestamp) < CACHE_DURATION:
        print("[Doctor] Using cached patients data")
        return _cache['patients']
    
    # Fetch fresh data from Google Sheets
    try:
        db = get_db()
        patients = db.get_patients()
        
        # Update cache
        _cache['patients'] = patients
        _cache_timestamp = current_time
        print(f"[Doctor] Fetched {len(patients)} patients from Google Sheets")
        return patients
    except Exception as e:
        print(f"[Doctor] Error fetching patients: {e}")
        # Return cached data even if expired, as fallback
        if 'patients' in _cache:
            print("[Doctor] Using stale cached data as fallback")
            return _cache['patients']
        raise

def get_patient_score(patient):
    """
    Extract and normalize patient severity score.
    Includes heuristic for locale-mangled decimals (e.g. 577 -> 57.7).
    """
    raw = patient.get('severity_score') or patient.get('score_gravite') or patient.get('score_gravité')
    if raw is None or raw == '':
        return 0
    try:
        if isinstance(raw, str):
            txt = raw.strip().lower().replace("/100", "").replace("%", "")
            txt = txt.replace(",", ".")
            value = float(txt)
        else:
            value = float(raw)
        
        # Heuristic for locale-mangled decimals (same as in SheetsDB)
        while value > 100 and value < 10000:
            value /= 10.0
            
        return max(0, min(100, round(value, 1)))
    except (ValueError, TypeError):
        return 0

@doctor_bp.route('/patients', methods=['GET'])
@jwt_required()
def get_doctor_patients():
    """
    Get patients assigned to the currently authenticated doctor.
    Returns filtered list sorted by severity (highest first).
    """
    current_user = get_jwt_identity()
    doctor_username = current_user
    
    try:
        # Use cached patients data to avoid hitting Google Sheets quota
        patients = get_patients_cached()
        
        # Filter patients by assigned doctor (medecin column)
        doctor_patients = []
        doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)
        print(f"[Doctor] Looking for patients assigned to: '{doctor_full_name}' (username: {doctor_username})")
        print(f"[Doctor] Total patients in database: {len(patients)}")
        
        # Debug: Show all patients and their medecin_assigne values
        for patient in patients:
            patient_id = patient.get('patient_id', 'unknown')
            assigned_doctor = patient.get('medecin_assigne', '')
            print(f"[Doctor] Patient {patient_id}: medecin_assigne='{assigned_doctor}'")
        
        for patient in patients:
            assigned_doctor = patient.get('medecin_assigne', '')
            patient_id = patient.get('patient_id', 'unknown')
            
            if assigned_doctor and assigned_doctor == doctor_full_name:
                status = str(patient.get('statut', '')).strip().lower()
                # Ignore treated or transferred patients in the active queue
                try: 
                    import unicodedata
                    status = unicodedata.normalize('NFKD', status).encode('ASCII', 'ignore').decode('utf-8')
                except:
                    pass
                
                if not (status.startswith('trait') or status.startswith('transf')):
                    patient['normalized_score'] = get_patient_score(patient)
                    doctor_patients.append(patient)
        
        print(f"[Doctor] Found {len(doctor_patients)} patients for {doctor_full_name}")
        
        # Sort by severity score (highest first), then by arrival time
        doctor_patients.sort(key=lambda p: (-p['normalized_score'], p.get('arrival_time', '')))
        
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
    """
    Update the status of a patient assigned to the authenticated doctor.
    Verifies the patient belongs to the doctor before updating.
    """
    current_user = get_jwt_identity()
    doctor_username = current_user
    
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Le statut est requis'}), 400
        
        # Use cached patients data
        patients = get_patients_cached()
        
        # Find patient by ID and verify it belongs to this doctor
        patient_found = False
        row_index = None
        
        for idx, patient in enumerate(patients, start=2):  # start=2 because row 1 is header
            if str(patient.get('patient_id', '')) == str(patient_id):
                assigned_doctor = patient.get('medecin_assigne', '')
                doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)
                if assigned_doctor and assigned_doctor == doctor_full_name:
                    patient_found = True
                    row_index = idx
                    break
                else:
                    return jsonify({
                        'success': False, 
                        'error': 'Patient non assigné à ce médecin'
                    }), 403
        
        if not patient_found:
            return jsonify({'success': False, 'error': 'Patient non trouvé ou non assigné à ce médecin'}), 404
        
        db = get_db()
        doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)
        status_value = str(new_status).strip()
        updates = {'statut': status_value}

        if status_value.lower().startswith('transf'):
            updates['mode_affectation'] = 'Transfert'
            updates['specialite_assignee'] = 'Externe'

        success = db.update_patient_fields(patient_id, updates)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Impossible de mettre à jour le patient dans Google Sheets'
            }), 500

        if status_value.lower().startswith('trait') or status_value.lower().startswith('transf'):
            doctor = db.find_doctor_by_name(doctor_full_name)
            if doctor is None:
                doctor = db.find_doctor_by_patient(patient_id)
            if doctor:
                db.release_doctor(doctor['doctor_id'], patient_id)
            db.archive_patient(patient_id, reason=f'status={status_value}')

        invalidate_cache()

        return jsonify({
            'success': True,
            'message': f'Status updated to "{status_value}"',
            'patient_id': patient_id,
            'new_status': status_value
        }), 200
        
    except Exception as e:
        print(f"[Doctor] Error updating status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@doctor_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_doctor_stats():
    """
    Get statistics for the authenticated doctor's patients.
    """
    current_user = get_jwt_identity()
    doctor_username = current_user
    
    try:
        db = get_db()
        patients_sheet = db._spreadsheet.worksheet("Patients")
        patients = patients_sheet.get_all_records()
        
        # Filter patients by assigned doctor
        doctor_patients = []
        for patient in patients:
            assigned_doctor = patient.get('medecin_assigne', '')
            doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)
            if assigned_doctor and assigned_doctor == doctor_full_name:
                status_val = str(patient.get('statut', '')).strip().lower()
                try: 
                    import unicodedata
                    status_val = unicodedata.normalize('NFKD', status_val).encode('ASCII', 'ignore').decode('utf-8')
                except:
                    pass
                if not (status_val.startswith('trait') or status_val.startswith('transf')):
                    doctor_patients.append(patient)
        
        # Calculate statistics
        total = len(doctor_patients)
        
        severity_distribution = {
            'critical': 0,
            'urgent': 0,
            'moderate': 0,
            'low': 0
        }
        
        status_distribution = {}
        
        for patient in doctor_patients:
            score = get_patient_score(patient)
            if score >= 80:
                severity_distribution['critical'] += 1
            elif score >= 60:
                severity_distribution['urgent'] += 1
            elif score >= 40:
                severity_distribution['moderate'] += 1
            else:
                severity_distribution['low'] += 1
            
            status = patient.get('statut', 'En attente')
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
    """
    Get archived patients (Traité / Transféré) for the authenticated doctor.
    Reads from the ArchivedPatients sheet.
    """
    current_user = get_jwt_identity()
    doctor_username = current_user
    doctor_full_name = DOCTOR_NAMES.get(doctor_username.lower(), doctor_username)

    try:
        db = get_db()
        archived_sheet = db._spreadsheet.worksheet("ArchivedPatients")
        all_archived = archived_sheet.get_all_records()

        # Filter by doctor
        doctor_history = [
            p for p in all_archived
            if str(p.get('medecin_assigne', '')).strip() == doctor_full_name
        ]

        # Sort by archived_at descending (most recent first)
        doctor_history.sort(
            key=lambda p: str(p.get('archived_at', '') or ''),
            reverse=True
        )

        # Normalize scores
        for p in doctor_history:
            p['normalized_score'] = get_patient_score(p)

        return jsonify({
            'success': True,
            'doctor_username': doctor_username,
            'total': len(doctor_history),
            'history': doctor_history
        }), 200

    except Exception as e:
        print(f"[Doctor] Error getting history: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

