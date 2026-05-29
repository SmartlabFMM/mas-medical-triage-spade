from unittest import result

from database.connection import db
from database.repositories import (
    PatientRepository,
    DoctorRepository,
    DecisionRepository,
    ResourceRepository,
    LogRepository,
    UserRepository,
    ArchivedPatientRepository
)
from database.models import Patient, Decision, Resource, Log, Doctor, User, ArchivedPatient
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class PGSheetsDB:
    def __init__(self):
        self.patient_repo = PatientRepository(db.session)
        self.doctor_repo = DoctorRepository(db.session)
        self.decision_repo = DecisionRepository(db.session)
        self.resource_repo = ResourceRepository(db.session)
        self.log_repo = LogRepository(db.session)
        self.user_repo = UserRepository(db.session)
        self.archived_repo = ArchivedPatientRepository(db.session)

    def get_patients(self, status=None, limit=100, offset=0):
        patients = self.patient_repo.get_all(status=status, limit=limit, offset=offset)
        result = []
        for p in patients:
            d = p.to_dict()
            # Convert UUID fields to strings for Pydantic compatibility
            d['patient_id'] = str(d['patient_id']) if d.get('patient_id') else None
            d['id'] = d['patient_id']  # agent uses 'id' key
            result.append(d)
        return result

    def insert_patient(self, patient_data):
        patient = self.patient_repo.create(patient_data)
        return patient.to_dict()

    def update_patient_status(self, patient_id, status, lit_assigne=None):
        updates = {'statut': status}
        if lit_assigne:
            updates['lit_assigne'] = lit_assigne
        self.patient_repo.update(patient_id, updates)
        return True

    def get_resources(self, limit=100, offset=0):
        resources = self.resource_repo.get_all(limit=limit, offset=offset)
        return [r.to_dict() for r in resources]

    def get_doctors(self, specialite=None, limit=100, offset=0):
        doctors = self.doctor_repo.get_all(limit=limit, offset=offset)
        doctor_dicts = [d.to_dict() if hasattr(d, 'to_dict') else d for d in doctors]
        if specialite:
            doctor_dicts = [d for d in doctor_dicts if d.get('specialite') == specialite]
        return doctor_dicts

    def insert_decision(self, decision_data):
        decision = self.decision_repo.create(decision_data)
        return True

    def get_decisions(self, patient_id=None, limit=100, offset=0):
        decisions = self.decision_repo.get_all(limit=limit, offset=offset)
        if patient_id:
            decisions = [d for d in decisions if str(d.patient_id) == patient_id]
        return [d.to_dict() for d in decisions]

    def log(self, agent, action, details="", patient_id="", niveau="INFO"):
        log_data = {
            'agent': agent,
            'action': action,
            'details': details,
            'patient_id': patient_id,
            'niveau': niveau,
            'timestamp': datetime.now()
        }
        self.log_repo.create(log_data)
        return True

    def get_logs(self, limit=100, offset=0):
        logs = self.log_repo.get_all(limit=limit, offset=offset)
        return [l.to_dict() for l in logs]

    def find_available_resource(self, resource_type):
        resources = self.resource_repo.search(disponibilite=True)
        for r in resources:
            r_dict = r.to_dict() if hasattr(r, 'to_dict') else r
            if resource_type.lower() in r_dict.get('nom_ressource', '').lower():
                return r_dict
        return None

    def upsert_resource(self, resource_data):
        nom = resource_data.get('nom_ressource')
        existing = self.resource_repo.get_by_id(nom)
        if existing:
            self.resource_repo.update(nom, resource_data)
        else:
            self.resource_repo.create(resource_data)
        return True

    def find_doctor_by_name(self, doctor_name):
        doctors = self.doctor_repo.search(nom=doctor_name)
        return doctors[0].to_dict() if doctors else None

    def find_available_doctor(self, specialty):
        doctors = self.doctor_repo.search(disponible=True)
        for doctor in doctors:
            d_dict = doctor.to_dict() if hasattr(doctor, 'to_dict') else doctor
            if d_dict.get('specialite', '').lower() == specialty.lower():
                return d_dict
        return None

    def assign_doctor(self, doctor_id, patient_id):
        doctor = self.doctor_repo.get_by_id(doctor_id)
        if doctor:
            doctor.patient_assigne = patient_id
            self.doctor_repo.update(doctor_id, {'patient_assigne': patient_id})
            return True
        return False

    # Migration helper methods
    def insert_doctor(self, doctor_data):
        doctor = self.doctor_repo.create(doctor_data)
        return doctor.to_dict()

    def insert_resource(self, resource_data):
        resource = self.resource_repo.create(resource_data)
        return resource.to_dict()