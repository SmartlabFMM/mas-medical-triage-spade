from sqlalchemy.orm import Session
from ..models import Doctor
from typing import List, Optional, Dict, Any


class DoctorRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> Doctor:
        obj = Doctor(**data)
        self.db.add(obj)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return obj

    def update(self, doctor_id: str, data: Dict[str, Any]) -> bool:
        obj = self.db.query(Doctor).get(doctor_id)
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

    def delete(self, doctor_id: str) -> bool:
        obj = self.db.query(Doctor).get(doctor_id)
        if not obj:
            return False
        self.db.delete(obj)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, doctor_id: str) -> Optional[Doctor]:
        return self.db.query(Doctor).get(doctor_id)

    def get_all(self, limit: int = 20, offset: int = 0) -> List[Doctor]:
        return self.db.query(Doctor).offset(offset).limit(limit).all()

    def search(self, **filters: Any) -> List[Doctor]:
        query = self.db.query(Doctor)
        for key, value in filters.items():
            if hasattr(Doctor, key):
                query = query.filter(getattr(Doctor, key) == value)
        return query.all()

    def count(self) -> int:
        return self.db.query(Doctor).count()
