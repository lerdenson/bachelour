import logging
from datetime import timedelta
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel


from repository import repository, models
import schemas
import security
from repository.database import engine
from utils import password
from config import config

# Import  service
from service.recipe_service import RecipeService

# Create DB tables on startup
models.Base.metadata.create_all(bind=engine)

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI App Initialization
app = FastAPI(
    title="Recipe Finder API",
    description="An API to find recipes and manage user preferences.",
    version="1.0" 
)

# --- CORS Middleware ---
origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Data Models ---

class QuestionRequest(BaseModel):
    question: str
    tags: List[str] = []

class NutritionInfo(BaseModel):
    calories: Optional[float] = None
    protein: Optional[float] = None
    carbohydrates: Optional[float] = None
    saturated_fat: Optional[float] = None
    monounsaturated_fat: Optional[float] = None
    polyunsaturated_fat: Optional[float] = None

    class Config:
        alias_generator = lambda string: string.replace(" ", "_")
        allow_population_by_field_name = True
        
class FormattedRecipe(BaseModel):
    dish_url: str
    dish_name: str
    ingredients: List[str]
    nutrition: NutritionInfo

class RecipeResponse(BaseModel):
    recipes: List[FormattedRecipe]

# --- Service Initialization ---
try:
    service = RecipeService(config=config)
except ValueError as e:
    logger.critical(f"Failed to initialize RecipeService: {e}")
    # Exit if the service can't be initialized (e.g., missing config)
    exit(1)


# --- USER & AUTHENTICATION ENDPOINTS (UNCHANGED) ---

@app.post("/api/v1/users/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(
    user: schemas.UserCreate, 
    user_repo: repository.UserRepository = Depends(repository.get_user_repository)
):
    db_user = user_repo.get_by_email(email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return user_repo.create(user_create=user)

@app.post("/api/v1/users/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_repo: repository.UserRepository = Depends(repository.get_user_repository)
):
    user = security.authenticate_user(
        user_repo=user_repo, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = password.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/v1/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(security.get_current_user)):
    return current_user

@app.put("/api/v1/users/me/preferences", response_model=schemas.User)
def update_preferences(
    preferences: schemas.Preferences,
    current_user: models.User = Depends(security.get_current_user),
    user_repo: repository.UserRepository = Depends(repository.get_user_repository)
):
    return user_repo.update_preferences(user=current_user, preferences=preferences)


# --- RECIPE ENDPOINT (ADAPTED FOR NEW SERVICE RESPONSE) ---

@app.post("/api/v1/recipes/ask", response_model=RecipeResponse)
async def ask_for_recipe(
    request: QuestionRequest,
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Accepts a user's question and tags, and returns a list of formatted recipes
    including names, URLs, ingredients, and nutrition info.
    """
    try:
        formatted_recipes = service.find_recipes(
            request=request,
            user=current_user
        )
        return RecipeResponse(recipes=formatted_recipes)

    except ValueError as e:
        logger.error(f"Service layer error for user {current_user.email}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("An unexpected error occurred while processing recipe request.")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@app.get("/")
def read_root():
    return {"status": "Recipe Finder API is running"}