# ============================================================
# [DEV MODE] Auth di-bypass untuk keperluan testing FE
# Untuk restore: uncomment blok ORIGINAL, comment blok MOCK
# ============================================================

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import User

# --- MOCK: Langsung return dummy user tanpa cek token ---
def get_current_user(request: Request, db: Session = Depends(get_db)):
    """
    [DEV MODE] Auth bypass - return mock user untuk FE testing.
    Restore dengan uncomment blok ORIGINAL di bawah.
    """
    # Cari user pertama di DB sebagai mock user
    mock_user = db.query(User).first()
    if mock_user:
        return mock_user
    
    # Jika DB kosong, buat object User dummy (tidak disimpan ke DB)
    dummy = User()
    dummy.id = "dev-mock-user-id"
    dummy.company_id = "dev-mock-company-id"
    dummy.name = "Dev Mock User"
    dummy.email = "dev@mock.com"
    dummy.role = "admin"
    return dummy

# --- ORIGINAL: Uncomment ini saat auth aktif kembali ---
# from fastapi.security import OAuth2PasswordBearer
# from app.services.auth import decode_access_token
# 
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# 
# def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     payload = decode_access_token(token)
#     if payload is None:
#         raise credentials_exception
#     user_id: str = payload.get("sub")
#     if user_id is None:
#         raise credentials_exception
#     user = db.query(User).filter(User.id == user_id).first()
#     if user is None:
#         raise credentials_exception
#     return user
