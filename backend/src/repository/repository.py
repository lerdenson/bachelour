from typing import Generic, List, Optional, Type, TypeVar
from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from repository import models
from repository.database import get_db
import schemas
from utils.password import get_password_hash

from sqlalchemy.ext.declarative import DeclarativeMeta

# Define TypeVars for generic repository
ModelType = TypeVar("ModelType", bound=DeclarativeMeta)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)

class BaseRepository(Generic[ModelType, CreateSchemaType]):
    """
    A generic base repository with common CRUD operations.
    """
    def __init__(self, model: Type[ModelType], db: Session):
        self.model = model
        self.db = db

    def get(self, id: int) -> Optional[ModelType]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        return self.db.query(self.model).offset(skip).limit(limit).all()


class UserRepository(BaseRepository[models.User, schemas.UserCreate]):
    """
    Repository specifically for User model operations.
    """
    def __init__(self, db: Session):
        # Pass the User model and the db session to the parent class
        super().__init__(models.User, db)

    def get_by_email(self, email: str) -> Optional[models.User]:
        """Fetches a user by their email address."""
        return self.db.query(self.model).filter(self.model.email == email).first()

    def create(self, user_create: schemas.UserCreate) -> models.User:
        """Creates a new user with a hashed password."""
        hashed_password = get_password_hash(user_create.password)
        db_user = self.model(email=user_create.email, hashed_password=hashed_password)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_preferences(
        self,
        user: models.User,
        preferences: schemas.Preferences
    ) -> models.User:
        """Updates a user's ingredient preferences."""
        user.prohibited_ingredients = preferences.prohibited_ingredients
        self.db.commit()
        self.db.refresh(user)
        return user

# --- FastAPI Dependency ---
# This function will be used in our API endpoints to get an instance
# of the UserRepository, which already has a db session.
def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return UserRepository(db)