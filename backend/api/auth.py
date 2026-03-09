from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from models.auth import SignupRequest, SigninRequest, Token
import os
from db import companies_collection

# Security Configurations
SECRET_KEY = os.getenv("JWT_SECRET", "SUPER_SECRET_KEY_FOR_STRATEGIC_GRID")
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

from dependencies import get_current_user
from fastapi import Depends, Body, UploadFile, File
import shutil
from bson import ObjectId

@router.get("/me")
async def get_my_profile(user=Depends(get_current_user)):
    """Get the current user company profile."""
    company = await companies_collection.find_one({"_id": ObjectId(user["company_id"])})
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
        
    return {
        "company_id": str(company["_id"]),
        "email": company.get("email", ""),
        "company_name": company.get("company_name", ""),
        "company_website_url": company.get("company_website_url", ""),
        "country": company.get("country", ""),
        "contact_person_name": company.get("contact_person_name", ""),
        "phone_number": company.get("phone_number", ""),
        "api_key": company.get("api_key", ""),
        "business_type": company.get("business_type", ""),
        "company_description": company.get("company_description", ""),
        "logo_url": company.get("logo_url", ""),
        "settings": company.get("settings", {})
    }

@router.patch("/settings")
async def update_settings(payload: dict = Body(...), user=Depends(get_current_user)):
    """Update company settings (like profile, keys, smtp, password, etc)"""
    updates = {}
    
    # Top level string fields
    top_level_fields = [
        "company_name", "company_website_url", "country",
        "contact_person_name", "email", "phone_number", "api_key",
        "business_type", "company_description", "logo_url"
    ]
    
    for field in top_level_fields:
        if field in payload:
            updates[field] = payload[field]
            
    # Handle password update securely
    if "password" in payload and payload["password"]:
        updates["password_hash"] = get_password_hash(payload["password"])
        
    # Handle nested settings dict (SMTP etc)
    if "settings" in payload and isinstance(payload["settings"], dict):
        for k, v in payload["settings"].items():
            updates[f"settings.{k}"] = v
            
    if not updates:
        return {"status": "success", "message": "No changes provided"}
        
    await companies_collection.update_one(
        {"_id": ObjectId(user["company_id"])},
        {"$set": updates}
    )
    
    return {"status": "success", "message": "Settings updated"}

@router.post("/upload-logo")
async def upload_logo(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """Upload a company logo and return its public URL."""
    try:
        # Generate a unique filename based on company ID to prevent collisions
        # We can just keep overwriting the same company's logo file
        os.makedirs("public/logos", exist_ok=True)
        filename = f"{user['company_id']}_{file.filename}"
        file_path = os.path.join("public", "logos", filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")
        public_url = f"{base_url}/public/logos/{filename}"
        
        # We don't automatically update the collection here, we let the frontend 
        # save it via PATCH /settings, but we could do it here as well.
        
        return {"status": "success", "logo_url": public_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
