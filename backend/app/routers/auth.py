from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import AuditLog, PatientProfile, RoleEnum, User
from app.schemas import TokenResponse, UserLogin, UserOut, UserRegister

router = APIRouter(prefix="/api/auth", tags=["auth"])

LEGACY_PASSWORDS = {
    "admin@example.com": ["Admin123!", "admin123"],
    "doctor@example.com": ["Doctor123!", "doctor123"],
    "patient@example.com": ["Patient123!", "secret123"],
}


def password_matches(password: str, user: User) -> bool:
    if verify_password(password, user.password_hash):
        return True
    for legacy_password in LEGACY_PASSWORDS.get(user.email.lower(), []):
        if password == legacy_password and verify_password(legacy_password, user.password_hash):
            return True
    return False


@router.post("/register", response_model=TokenResponse)
def register_user(payload: UserRegister, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(email=email, password_hash=hash_password(payload.password), role=RoleEnum.PATIENT.value, is_active=True)
    db.add(user)
    db.flush()
    profile = PatientProfile(user_id=user.id, full_name=payload.full_name)
    db.add(profile)
    db.add(AuditLog(user_id=user.id, action="user_registered", details={"role": user.role}))
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if not user or not password_matches(payload.password, user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    profile = current_user.patient_profile or current_user.doctor_profile
    full_name = getattr(profile, "full_name", None) or getattr(profile, "name", None)
    return UserOut(id=current_user.id, email=current_user.email, role=current_user.role, full_name=full_name)
