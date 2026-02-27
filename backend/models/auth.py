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

class SigninRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
