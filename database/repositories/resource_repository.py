from sqlalchemy.orm import Session
from ..models import Resource
from typing import List, Optional, Dict, Any


class ResourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> Resource:
        obj = Resource(**data)
        self.db.add(obj)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return obj

    def update(self, nom_ressource: str, data: Dict[str, Any]) -> bool:
        obj = self.db.query(Resource).get(nom_ressource)
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

    def delete(self, nom_ressource: str) -> bool:
        obj = self.db.query(Resource).get(nom_ressource)
        if not obj:
            return False
        self.db.delete(obj)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, nom_ressource: str) -> Optional[Resource]:
        return self.db.query(Resource).get(nom_ressource)

    def get_all(self, limit: int = 20, offset: int = 0) -> List[Resource]:
        return self.db.query(Resource).offset(offset).limit(limit).all()

    def search(self, **filters: Any) -> List[Resource]:
        query = self.db.query(Resource)
        for key, value in filters.items():
            if hasattr(Resource, key):
                query = query.filter(getattr(Resource, key) == value)
        return query.all()

    def search_by_type(self, resource_type: str) -> List[Resource]:
        """Return resources where nom_ressource contains the given type string (case-insensitive)."""
        return self.db.query(Resource).filter(Resource.nom_ressource.ilike(f"%{resource_type}%")).all()
        # existing filter search
        ...
        query = self.db.query(Resource)
        for key, value in filters.items():
            if hasattr(Resource, key):
                query = query.filter(getattr(Resource, key) == value)
        return query.all()

    def filter_by_statut(self, statut: str) -> List[Resource]:
        return self.db.query(Resource).filter(Resource.statut == statut).all()

    def count(self) -> int:
        return self.db.query(Resource).count()
