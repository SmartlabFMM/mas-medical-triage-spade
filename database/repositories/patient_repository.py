from sqlalchemy.orm import Session
from ..models import Patient
from typing import List, Optional, Dict, Any


class PatientRepository:
    def get_occupied_beds(self):
        """Return a list of bed IDs (lit_assigne) for patients that are currently occupying a bed.
        Beds are considered occupied if patient.status is not 'traité' or 'transféré' and lit_assigne is set.
        """
        occupied = []
        patients = self.db.query(Patient).filter(Patient.lit_assigne != None).all()
        for p in patients:
            if p.statut and not p.statut.lower().startswith('trait') and not p.statut.lower().startswith('transf'):
                occupied.append(p.lit_assigne)
        return occupied
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> Patient:
        # Filter out any keys that are not actual Patient columns
        valid_cols = {c.key for c in Patient.__table__.columns}
        clean_data = {k: v for k, v in data.items() if k in valid_cols}
        patient = Patient(**clean_data)
        self.db.add(patient)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return patient

    def update(self, patient_id: str, data: Dict[str, Any]) -> bool:
        patient = self.db.query(Patient).get(patient_id)
        if not patient:
            return False
        for key, value in data.items():
            setattr(patient, key, value)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, patient_id: str) -> bool:
        patient = self.db.query(Patient).get(patient_id)
        if not patient:
            return False
        self.db.delete(patient)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, patient_id: str) -> Optional[Patient]:
        return self.db.query(Patient).get(patient_id)

    def get_all(self, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[Patient]:
        query = self.db.query(Patient)
        if status:
            query = query.filter(Patient.statut == status)
        return query.offset(offset).limit(limit).all()

    def search(self, **filters: Any) -> List[Patient]:
        query = self.db.query(Patient)
        for key, value in filters.items():
            if hasattr(Patient, key):
                query = query.filter(getattr(Patient, key) == value)
        return query.all()

    def filter_by_status(self, status: str) -> List[Patient]:
        return self.db.query(Patient).filter(Patient.statut == status).all()

    def count(self) -> int:
        return self.db.query(Patient).count()
