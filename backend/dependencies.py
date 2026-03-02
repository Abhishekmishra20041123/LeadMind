from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from bson import ObjectId
from db import companies_collection
import os

SECRET_KEY = os.getenv("JWT_SECRET", "SUPER_SECRET_KEY_FOR_STRATEGIC_GRID")
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/signin")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        company_id: str = payload.get("company_id")
        if email is None or company_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    company = await companies_collection.find_one({"_id": ObjectId(company_id)})
    if company is None:
        raise credentials_exception
        
    return {
        "email": email,
        "company_id": ObjectId(company_id),
        "settings": company.get("settings", {})
    }
