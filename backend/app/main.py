import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.models import DoctorProfile, DoctorWorkingHour, User
from app.routers.admin import router as admin_router
from app.routers.appointments import router as appointments_router
from app.routers.auth import router as auth_router
from app.routers.doctors import router as doctors_router

settings = get_settings()


def seed_demo_data() -> None:
    db_url = (os.getenv("DATABASE_URL") or settings.database_url or "").lower()
    app_env = (os.getenv("APP_ENV") or "").lower()
    if app_env == "test" or "test" in db_url:
        return

    with SessionLocal() as db:
        admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin_user:
            admin_user = User(email="admin@example.com", password_hash=hash_password("admin123"), role="admin", is_active=True)
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        doctor_user = db.query(User).filter(User.email == "doctor@example.com").first()
        if not doctor_user:
            doctor_user = User(email="doctor@example.com", password_hash=hash_password("doctor123"), role="doctor", is_active=True)
            db.add(doctor_user)
            db.commit()
            db.refresh(doctor_user)

        if not db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_user.id).first():
            doctor = DoctorProfile(user_id=doctor_user.id, name="Dr. Priya Sharma", specialization="Cardiology", qualification="MD, Cardiology", experience_years=10, slot_duration_minutes=30, is_active=True)
            db.add(doctor)
            db.commit()
            db.refresh(doctor)
            db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=0, start_time="09:00", end_time="13:00"))
            db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=2, start_time="10:00", end_time="14:00"))
            db.commit()

        patient_user = db.query(User).filter(User.email == "patient@example.com").first()
        if not patient_user:
            patient_user = User(email="patient@example.com", password_hash=hash_password("secret123"), role="patient", is_active=True)
            db.add(patient_user)
            db.commit()


settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    Base.metadata.create_all(bind=engine)
    seed_demo_data()


@app.exception_handler(Exception)
async def generic_exception_handler(_, exc):
    return JSONResponse(status_code=500, content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred."}})


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api")
def api_root():
    return {"message": settings.app_name, "endpoints": ["/api/auth/login", "/api/auth/register", "/api/doctors", "/api/appointments"]}


app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(admin_router)
