import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User, Company
from app.api.schemas import UserRegister, Token, UserResponse
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import get_password_hash, verify_password, create_access_token

router = APIRouter()

@router.post("/register", response_model=UserResponse)
def register_user(user_in: UserRegister, db: Session = Depends(get_db)):
    # Check if user exists
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Check if company slug exists
    company = db.query(Company).filter(Company.slug == user_in.company_slug).first()
    if company:
        raise HTTPException(status_code=400, detail="Company slug already taken")
        
    # Create Company
    new_company_id = str(uuid.uuid4())
    new_company = Company(
        id=new_company_id,
        name=user_in.company_name,
        slug=user_in.company_slug,
        status="active"
    )
    db.add(new_company)
    
    # Create User
    new_user_id = str(uuid.uuid4())
    new_user = User(
        id=new_user_id,
        company_id=new_company_id,
        name=user_in.name,
        email=user_in.email,
        password=get_password_hash(user_in.password),
        role="admin"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@router.post("/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": user.id, "company_id": user.company_id, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}
