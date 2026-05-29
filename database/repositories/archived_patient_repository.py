from sqlalchemy.orm import Session
from ..models import ArchivedPatient
from typing import List, Optional, Dict, Any


class ArchivedPatientRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> ArchivedPatient:
        obj = ArchivedPatient(**data)
        self.db.add(obj)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return obj

    def update(self, patient_id: str, data: Dict[str, Any]) -> bool:
        obj = self.db.query(ArchivedPatient).get(patient_id)
        if not obj:
            return False
        for key, value in data.items():
            setattr(obj, key, value)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, patient_id: str) -> bool:
        obj = self.db.query(ArchivedPatient).get(patient_id)
        if not obj:
            return False
        self.db.delete(obj)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, patient_id: str) -> Optional[ArchivedPatient]:
        return self.db.query(ArchivedPatient).get(patient_id)

    def get_all(self, status: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[ArchivedPatient]:
        query = self.db.query(ArchivedPatient)
        if status:
            query = query.filter(ArchivedPatient.statut == status)
        return query.offset(offset).limit(limit).all()

    def search(self, **filters: Any) -> List[ArchivedPatient]:
        query = self.db.query(ArchivedPatient)
        for key, value in filters.items():
            if hasattr(ArchivedPatient, key):
                query = query.filter(getattr(ArchivedPatient, key) == value)
        return query.all()

    def count(self) -> int:
        return self.db.query(ArchivedPatient).count()
