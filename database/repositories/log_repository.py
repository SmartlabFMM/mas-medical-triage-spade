from sqlalchemy.orm import Session
from ..models import Log
from typing import List, Optional, Dict, Any


class LogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> Log:
        obj = Log(**data)
        self.db.add(obj)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return obj

    def update(self, log_id: str, data: Dict[str, Any]) -> bool:
        obj = self.db.query(Log).get(log_id)
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

    def delete(self, log_id: str) -> bool:
        obj = self.db.query(Log).get(log_id)
        if not obj:
            return False
        self.db.delete(obj)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, log_id: str) -> Optional[Log]:
        return self.db.query(Log).get(log_id)

    def get_all(self, limit: int = 20, offset: int = 0) -> List[Log]:
        return self.db.query(Log).offset(offset).limit(limit).all()

    def search(self, **filters: Any) -> List[Log]:
        query = self.db.query(Log)
        for key, value in filters.items():
            if hasattr(Log, key):
                query = query.filter(getattr(Log, key) == value)
        return query.all()

    def count(self) -> int:
        return self.db.query(Log).count()
