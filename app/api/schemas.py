from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserRegister(BaseModel):
    company_name: str
    company_slug: str
    name: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    company_id: Optional[str] = None
    role: str

    class Config:
        from_attributes = True

# --- Job Schemas ---
class JobCreate(BaseModel):
    title: str
    slug: str
    location: str
    department: str
    experience_level: str
    description: str
    requirements: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "IDR"
    openings: int = 1

class JobResponse(JobCreate):
    id: str
    company_id: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# --- Applicant Schemas ---
class ApplicantResponse(BaseModel):
    id: str
    name: str
    email: str
    status: str
    overall_score: Optional[int] = None
    cv_summary: Optional[str] = None
    
    class Config:
        from_attributes = True
