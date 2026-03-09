from pydantic import BaseModel, EmailStr, HttpUrl
from typing import Optional

class SignupRequest(BaseModel):
    company_name: str
    company_website_url: HttpUrl
    country: str
    contact_person_name: str
    email: EmailStr
    phone_number: str
    password: str
    business_type: Optional[str] = None
    company_description: Optional[str] = None

class SigninRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
