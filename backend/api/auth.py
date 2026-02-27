from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from models.auth import SignupRequest, SigninRequest, Token
from db import companies_collection

# Security Configurations
SECRET_KEY = "SUPER_SECRET_KEY_FOR_STRATEGIC_GRID" # Normally from env var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@router.post("/signup", response_model=Token)
async def signup(request: SignupRequest):
    # Check if business email is a gmail (rudimentary check per requirements)
    if "gmail.com" in request.email.lower():
        raise HTTPException(status_code=400, detail="Personal emails are not permitted. Use an official business email.")

    # Check if company already exists
    existing_user = await companies_collection.find_one({"email": request.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Operator with this email already exists in the grid.")
    
    # Store
    company_dict = request.dict()
    company_dict["password_hash"] = get_password_hash(company_dict.pop("password"))
    company_dict["created_at"] = datetime.utcnow()
    company_dict["company_website_url"] = str(company_dict["company_website_url"]) 

    result = await companies_collection.insert_one(company_dict)
    
    # Issue token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.email, "company_id": str(result.inserted_id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/signin", response_model=Token)
async def signin(request: SigninRequest):
    # Verify User
    company = await companies_collection.find_one({"email": request.email})
    if not company:
        raise HTTPException(status_code=401, detail="Invalid operator ID or security key")
    
    if not verify_password(request.password, company["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid operator ID or security key")
    
    # Issue Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": company["email"], "company_id": str(company["_id"])}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
