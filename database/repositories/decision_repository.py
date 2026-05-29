from sqlalchemy.orm import Session
from ..models import Decision
from typing import List, Optional, Dict, Any


class DecisionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> Decision:
        obj = Decision(**data)
        self.db.add(obj)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return obj

    def update(self, decision_id: str, data: Dict[str, Any]) -> bool:
        obj = self.db.query(Decision).get(decision_id)
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

    def delete(self, decision_id: str) -> bool:
        obj = self.db.query(Decision).get(decision_id)
        if not obj:
            return False
        self.db.delete(obj)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, decision_id: str) -> Optional[Decision]:
        return self.db.query(Decision).get(decision_id)

    def get_all(self, limit: int = 20, offset: int = 0) -> List[Decision]:
        return self.db.query(Decision).offset(offset).limit(limit).all()

    def search(self, **filters: Any) -> List[Decision]:
        query = self.db.query(Decision)
        for key, value in filters.items():
            if hasattr(Decision, key):
                query = query.filter(getattr(Decision, key) == value)
        return query.all()

    def count(self) -> int:
        return self.db.query(Decision).count()
