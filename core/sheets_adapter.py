"""Minimal adapter so agents can keep calling SheetsDB-like methods
while the real backend is PostgreSQL (via PGSheetsDB).
This is only a compatibility shim until agents are refactored."""
from unittest import result

from core.postgres_db import PGSheetsDB
from database.models import Patient
from flask import current_app
import os
import datetime

# Mapping from agent (English) field names to database (French) field names
FIELD_MAPPING = {
    'id': 'patient_id',
    'name': 'nom',
    'gender': 'genre',
    'symptoms': 'symptomes',
    # 'pain_level' has no corresponding column in Patient, so it is omitted
    'arrival_time': 'heure_arrivee',
}

# Translation map for English symptom names to French display names
SYMPTOMS_MAP = {
    'chest_pain': 'douleur thoracique',
    'shortness_of_breath': 'difficulté respiratoire',
    'headache': 'mal de tête',
    'nausea': 'nausée',
    'fever': 'fièvre',
    'high_fever': 'fièvre élevée',
    'vomiting': 'vomissements',
    'dizziness': 'vertiges',
    'abdominal_pain': 'douleur abdominale',
    'back_pain': 'douleur dorsale',
    'arm_pain': 'douleur bras',
    'sweating': 'transpiration',
    'palpitations': 'palpitations',
    'unconscious': 'inconscient',
    'bleeding': 'saignement',
    'fracture': 'fracture',
    'trauma': 'traumatisme',
}



class SheetsAdapter:
    def __init__(self, credentials_path=None, spreadsheet_name=None):
        self._pg = PGSheetsDB()

    def _get_app(self):
        """Get Flask app instance for application context."""
        # Import here to avoid circular imports
        from api.app import app
        return app

    def _with_app(self, func, *args, **kwargs):
        """Execute a function within Flask app context and return its result."""
        with self._get_app().app_context():
            return func(*args, **kwargs)


    @property
    def patient_repo(self):
        return self._pg.patient_repo
    def connect(self):
        """No-op (PostgreSQL is already connected)."""
        return self

    # ── Patient operations ──────────────────────────────────────
    def get_patients(self, status=None, limit=100, offset=0):
        with self._get_app().app_context():
            return self._pg.get_patients(status=status, limit=limit, offset=offset)
        patients = []
        result = []
        for p in patients:
            d = p.to_dict()
            # Ensure all UUID fields are strings
            if 'patient_id' in d and d['patient_id'] is not None:
                d['patient_id'] = str(d['patient_id'])
            d['id'] = d.get('patient_id', '')  # agent expects 'id' key
            result.append(d)
        return result

    def upsert_patient(self, patient_data):
        # Translate English keys to French/DB field names using FIELD_MAPPING
        mapped_data = {}
        for k, v in patient_data.items():
            new_key = FIELD_MAPPING.get(k, k)  # translate or keep original
            mapped_data[new_key] = v

        # Keep only columns that actually exist on the Patient model
        valid_cols = {c.key for c in Patient.__table__.columns}
        clean_data = {k: v for k, v in mapped_data.items() if k in valid_cols}

        patient_id = clean_data.get('patient_id')
        if not patient_id:
            return

        with self._get_app().app_context():
            existing = self._pg.patient_repo.get_by_id(patient_id)
            if existing:
                self._pg.patient_repo.update(patient_id, clean_data)
            else:
                self._pg.insert_patient(clean_data)  # use clean_data

    def update_patient_fields(self, patient_id, updates):
        # Translate any English keys in the updates dict
        mapped_updates = {}
        for k, v in updates.items():
            new_key = FIELD_MAPPING.get(k, k)
            mapped_updates[new_key] = v
        # Keep only valid columns
        valid_cols = {c.key for c in Patient.__table__.columns}
        clean_updates = {k: v for k, v in mapped_updates.items() if k in valid_cols}
        with self._get_app().app_context():
            self._pg.patient_repo.update(patient_id, clean_updates)

    def update_patient_decision(self, patient_id, action, score, status):
        """Mirror the old SheetsDB.update_patient_decision()."""
        with self._get_app().app_context():
            # Update patient action/status
            self._pg.patient_repo.update(patient_id, {
                'action_finale': action,
                'statut': status,
                'score_gravite': float(score) if score else None,
            })
            # Insert decision record
            if score is not None:
                self._pg.insert_decision({
                    'patient_id': patient_id,
                    'score_gravite': float(score),
                    'action': action,
                    'raisonnement': f'Decision: {action}',
                    'nb_cycles': 1,
                    'timestamp': datetime.datetime.now(datetime.timezone.utc),
                    'agent_decideur': 'MetaAgent',
                })

    def update_patient_bed(self, patient_id, bed_id):
        with self._get_app().app_context():
            self._pg.patient_repo.update(patient_id, {'lit_assigne': bed_id})

    def update_patient_doctor_assignment(self, patient_id, doctor_name, specialty, mode=None, **kwargs):
        with self._get_app().app_context():
            updates = {'medecin_assigne': doctor_name}
            if specialty:
                updates['specialite_assignee'] = specialty
            if mode:
                updates['mode_affectation'] = mode
            self._pg.patient_repo.update(patient_id, updates)

    # ── Doctor operations ──────────────────────────────────────
    def find_available_doctor(self, specialty):
        with self._get_app().app_context():
            return self._pg.find_available_doctor(specialty)

    def assign_doctor(self, doctor_id, patient_id):
        with self._get_app().app_context():
            return self._pg.assign_doctor(doctor_id, patient_id)

    def insert_decision(self, decision_data):
        DECISION_MAPPING = {
            'severity_score': 'score_gravite',
            'rationale':      'raisonnement',
            'decided_by':     'agent_decideur',
            'cycle_count':    'nb_cycles',
        }
        mapped = {DECISION_MAPPING.get(k, k): v for k, v in decision_data.items()}
        with self._get_app().app_context():
            return self._pg.insert_decision(mapped)

    # ── Resource operations ────────────────────────────────────
    def get_availability_summary(self):
        with self._get_app().app_context():
            # Get all resources
            resources = self._pg.resource_repo.get_all()
            # Get all occupied beds (lit_assigne not None and status not in ["traité", "transféré"])
            occupied_beds = self._pg.patient_repo.get_occupied_beds()
            beds_total = sum(1 for r in resources if 'lit' in str(r.nom_ressource).lower())
            beds_avail = beds_total - len(occupied_beds)
            # Count specialties - match on resource name
            cardio_avail = sum(1 for r in resources if 'cardio' in str(r.nom_ressource).lower() and r.nom_ressource not in occupied_beds)
            neuro_avail = sum(1 for r in resources if 'neuro' in str(r.nom_ressource).lower() and r.nom_ressource not in occupied_beds)
            trauma_avail = sum(1 for r in resources if 'trauma' in str(r.nom_ressource).lower() and r.nom_ressource not in occupied_beds)
            general_avail = sum(1 for r in resources if 'general' in str(r.nom_ressource).lower() and r.nom_ressource not in occupied_beds)
            return {
                'lits': {'total': beds_total, 'disponibles': beds_avail},
                'cardio': {'disponibles': cardio_avail},
                'neuro': {'disponibles': neuro_avail},
                'trauma': {'disponibles': trauma_avail},
                'general': {'disponibles': general_avail},
            }

    def find_available_resource(self, resource_type):
        with self._get_app().app_context():
            # Get all resources of the given type
            resources = self._pg.resource_repo.search_by_type(resource_type)
            # Get all occupied beds
            occupied_beds = self._pg.patient_repo.get_occupied_beds()
            for r in resources:
                if r.nom_ressource not in occupied_beds:
                    return r.to_dict()
            return None

    def allocate_resource(self, resource_type, patient_id, patient_name,  action=None):
        """Allocate a bed/resource to a patient, update status."""
        with self._get_app().app_context():
            # Find an available bed
            bed = self.find_available_resource(resource_type)
            if bed:
                # Update patient's bed assignment
                self.update_patient_bed(patient_id, bed['nom_ressource'])
                return True
            return False

    # ── Logging ────────────────────────────────────────────────
    def log(self, agent, action, details="", patient_id="", niveau="INFO"):
        with self._get_app().app_context():
            self._pg.log(agent, action, details=details, patient_id=patient_id, niveau=niveau)


