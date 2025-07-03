from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

# Import the repository and its dependency function
from repository.repository import UserRepository, get_user_repository
from repository import models
import schemas
from utils.password import verify_password, decode_access_token


ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

# --- Password Hashing (remains the same) ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- Authentication & Authorization (UPDATED) ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")

def authenticate_user(
    user_repo: UserRepository,
    email: str,
    password: str
) -> Optional[models.User]:
    """Authenticates a user using the UserRepository."""
    user = user_repo.get_by_email(email=email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository)
) -> models.User:
    """Decodes JWT and retrieves the current user via the UserRepository."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    user = user_repo.get_by_email(email=token_data.email)
    if user is None:
        raise credentials_exception
    return user