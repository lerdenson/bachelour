from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr


# --- Preference Schema ---
class Preferences(BaseModel):
    # --- CHANGED ---
    prohibited_ingredients: List[str] = []

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str

class User(UserBase, Preferences): # <-- It now inherits the new Preferences schema
    id: int

    class Config:
        orm_mode = True



# ===================================================================
#                     Authentication Schemas
# ===================================================================

class Token(BaseModel):
    """
    Schema for the response when a user successfully logs in.
    """
    access_token: str
    token_type: str


class TokenData(BaseModel):
    """
    Schema representing the data we expect to find inside a JWT payload.
    In our case, it's the user's email address (the 'sub' or subject claim).
    """
    email: Optional[str] = None


# ===================================================================
#                     Recipe Request & Response Schemas
# ===================================================================

class QuestionRequest(BaseModel):
    """
    Defines the structure of the request body for the /recipes/ask endpoint.
    This is the main input from the frontend to ask for recipes.
    """
    question: str
    question_type: str = "personalized"
    topic_entities: List[str] = []
    entities: List[str] = []
    # The persona field allows for on-the-fly preference adjustments.
    persona: Optional[Dict] = {}
    guideline: Optional[Dict] = None
    explicit_nutrition: Optional[List[str]] = []
    similar_recipes: Optional[Dict] = {}


class Recipe(BaseModel):
    """
    Schema for a single recipe object in the response list.
    """
    id: str
    name: str


class RecipeResponse(BaseModel):
    """
    Schema for the entire successful response from the /recipes/ask endpoint.
    """
    recipes: List[Recipe]