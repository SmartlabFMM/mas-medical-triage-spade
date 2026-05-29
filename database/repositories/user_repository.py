from sqlalchemy.orm import Session
from ..models import User
from typing import List, Optional, Dict, Any


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: Dict[str, Any]) -> User:
        user = User(**data)
        self.db.add(user)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            raise e
        return user

    def update(self, user_id: str, data: Dict[str, Any]) -> bool:
        user = self.db.query(User).get(user_id)
        if not user:
            return False
        for key, value in data.items():
            setattr(user, key, value)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def delete(self, user_id: str) -> bool:
        user = self.db.query(User).get(user_id)
        if not user:
            return False
        self.db.delete(user)
        try:
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).get(user_id)

    def get_all(self, role: Optional[str] = None, limit: int = 20, offset: int = 0) -> List[User]:
        query = self.db.query(User)
        if role:
            query = query.filter(User.role == role)
        return query.offset(offset).limit(limit).all()

    def search(self, **filters: Any) -> List[User]:
        query = self.db.query(User)
        for key, value in filters.items():
            if hasattr(User, key):
                query = query.filter(getattr(User, key) == value)
        return query.all()

    def count(self) -> int:
        return self.db.query(User).count()