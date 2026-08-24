import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
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


def ensure_doctor_profile_columns() -> None:
    if "sqlite" not in (os.getenv("DATABASE_URL") or settings.database_url or "").lower():
        return

    with engine.begin() as conn:
        table_exists = conn.execute(text("SELECT 1 FROM sqlite_master WHERE type='table' AND name='doctor_profiles'")).fetchone()
        if not table_exists:
            return

        columns = conn.execute(text("PRAGMA table_info(doctor_profiles)")).fetchall()
        existing = {row[1] for row in columns}
        for name, column_type in {
            "profile_photo_url": "VARCHAR(500)",
            "bio": "TEXT",
            "languages": "VARCHAR(255)",
            "consultation_fee": "INTEGER",
            "clinic_name": "VARCHAR(255)",
            "status": "VARCHAR(50)",
            "next_leave_date": "DATE",
            "return_to_work_date": "DATE",
        }.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE doctor_profiles ADD COLUMN {name} {column_type}"))


def seed_demo_data() -> None:
    db_url = (os.getenv("DATABASE_URL") or settings.database_url or "").lower()
    app_env = (os.getenv("APP_ENV") or "").lower()
    if app_env == "test" or "test" in db_url:
        return

    doctor_seed = [
        {
            "email": "doctor1@example.com",
            "password": "doctor123",
            "full_name": "Dr. Priya Sharma",
            "specialization": "Cardiologist",
            "qualification": "MD, Cardiology",
            "experience_years": 12,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=400&q=80",
            "bio": "Cardiology specialist focused on preventive care and heart health management.",
            "languages": "English, Hindi",
            "consultation_fee": 1200,
            "clinic_name": "Aster Heart Clinic",
            "status": "available",
        },
        {
            "email": "doctor2@example.com",
            "password": "doctor123",
            "full_name": "Dr. Aakash Mehta",
            "specialization": "General Physician",
            "qualification": "MBBS, MD",
            "experience_years": 9,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?auto=format&fit=crop&w=400&q=80",
            "bio": "General physician delivering primary care and long-term wellness planning.",
            "languages": "English, Marathi",
            "consultation_fee": 900,
            "clinic_name": "WellCare Family Clinic",
            "status": "available",
        },
        {
            "email": "doctor3@example.com",
            "password": "doctor123",
            "full_name": "Dr. Nisha Verma",
            "specialization": "Dermatologist",
            "qualification": "MD, Dermatology",
            "experience_years": 11,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1594824476967-48c8b964273f?auto=format&fit=crop&w=400&q=80",
            "bio": "Dermatology specialist for skin health, acne care, and aesthetic consultations.",
            "languages": "English, Hindi",
            "consultation_fee": 1100,
            "clinic_name": "Bloom Skin Center",
            "status": "available",
        },
        {
            "email": "doctor4@example.com",
            "password": "doctor123",
            "full_name": "Dr. Rohan Kapoor",
            "specialization": "Pediatrician",
            "qualification": "MD, Pediatrics",
            "experience_years": 8,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
            "bio": "Pediatrician focused on child wellness, vaccination, and growth monitoring.",
            "languages": "English, Hindi, Punjabi",
            "consultation_fee": 950,
            "clinic_name": "Sunrise Pediatric Clinic",
            "status": "available",
        },
        {
            "email": "doctor5@example.com",
            "password": "doctor123",
            "full_name": "Dr. Sneha Iyer",
            "specialization": "Orthopedic",
            "qualification": "MS, Orthopedics",
            "experience_years": 13,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=400&q=80",
            "bio": "Orthopedic specialist for joint, bone, and mobility rehabilitation.",
            "languages": "English, Tamil",
            "consultation_fee": 1300,
            "clinic_name": "MotionCare Orthopaedics",
            "status": "available",
        },
        {
            "email": "doctor6@example.com",
            "password": "doctor123",
            "full_name": "Dr. Kavya Nair",
            "specialization": "Gynecologist",
            "qualification": "MD, Obstetrics & Gynecology",
            "experience_years": 10,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=400&q=80",
            "bio": "Gynecologist managing preventive care, women’s health, and pregnancy support.",
            "languages": "English, Malayalam",
            "consultation_fee": 1150,
            "clinic_name": "Harmony Women’s Hospital",
            "status": "available",
        },
        {
            "email": "doctor7@example.com",
            "password": "doctor123",
            "full_name": "Dr. Arjun Sen",
            "specialization": "ENT Specialist",
            "qualification": "MS, ENT",
            "experience_years": 7,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=400&q=80",
            "bio": "ENT specialist treating ear, nose, throat, and sinus-related conditions.",
            "languages": "English, Bengali",
            "consultation_fee": 1050,
            "clinic_name": "ClearVoice ENT Center",
            "status": "available",
        },
        {
            "email": "doctor8@example.com",
            "password": "doctor123",
            "full_name": "Dr. Meera Joshi",
            "specialization": "Neurologist",
            "qualification": "DM, Neurology",
            "experience_years": 14,
            "slot_duration_minutes": 30,
            "profile_photo_url": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=400&q=80",
            "bio": "Neurologist focused on migraine management, neurological assessments, and follow-up care.",
            "languages": "English, Hindi, Kannada",
            "consultation_fee": 1400,
            "clinic_name": "NeuroWell Institute",
            "status": "available",
        },
    ]

    with SessionLocal() as db:
        required_users = {
            "admin@example.com": ("Admin123!", "admin"),
            "doctor@example.com": ("Doctor123!", "doctor"),
            "patient@example.com": ("Patient123!", "patient"),
        }
        for email, (password, role) in required_users.items():
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, password_hash=hash_password(password), role=role, is_active=True)
                db.add(user)
                db.commit()
                db.refresh(user)
            else:
                user.password_hash = hash_password(password)
                user.role = role
                user.is_active = True
                db.commit()

        admin_user = db.query(User).filter(User.email == "admin@example.com").first()
        doctor_default = db.query(User).filter(User.email == "doctor@example.com").first()

        if doctor_default and not db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_default.id).first():
            doctor = DoctorProfile(
                user_id=doctor_default.id,
                name="Dr. Maya Patel",
                specialization="General Physician",
                qualification="MBBS, MD",
                experience_years=10,
                slot_duration_minutes=30,
                profile_photo_url="https://images.unsplash.com/photo-1559839734-2b71ea197ec2?auto=format&fit=crop&w=400&q=80",
                bio="General physician focused on preventive care, chronic disease management, and patient education.",
                languages="English, Hindi",
                consultation_fee=900,
                clinic_name="CityCare Clinic",
                status="available",
                is_active=True,
            )
            db.add(doctor)
            db.commit()
            db.refresh(doctor)
            for weekday in range(5):
                db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=weekday, start_time="09:00", end_time="13:00"))
                db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=weekday, start_time="14:00", end_time="17:00"))
            db.commit()

        for doctor_item in doctor_seed:
            user = db.query(User).filter(User.email == doctor_item["email"]).first()
            if not user:
                user = User(email=doctor_item["email"], password_hash=hash_password(doctor_item["password"]), role="doctor", is_active=True)
                db.add(user)
                db.commit()
                db.refresh(user)

            if not db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first():
                doctor = DoctorProfile(
                    user_id=user.id,
                    name=doctor_item["full_name"],
                    specialization=doctor_item["specialization"],
                    qualification=doctor_item["qualification"],
                    experience_years=doctor_item["experience_years"],
                    slot_duration_minutes=doctor_item["slot_duration_minutes"],
                    profile_photo_url=doctor_item.get("profile_photo_url"),
                    bio=doctor_item.get("bio"),
                    languages=doctor_item.get("languages"),
                    consultation_fee=doctor_item.get("consultation_fee", 0),
                    clinic_name=doctor_item.get("clinic_name"),
                    status=doctor_item.get("status", "available"),
                    is_active=True,
                )
                db.add(doctor)
                db.commit()
                db.refresh(doctor)

                for weekday in range(5):
                    db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=weekday, start_time="09:00", end_time="13:00"))
                    db.add(DoctorWorkingHour(doctor_id=doctor.id, weekday=weekday, start_time="14:00", end_time="17:00"))
                db.commit()

        patient_seed = [
            ("patient@example.com", "Patient123!", "Patient One"),
            ("patient2@example.com", "secret123", "Patient Two"),
            ("patient3@example.com", "secret123", "Patient Three"),
        ]
        for email, password, full_name in patient_seed:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email, password_hash=hash_password(password), role="patient", is_active=True)
                db.add(user)
                db.commit()
                db.refresh(user)



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
    ensure_doctor_profile_columns()
    seed_demo_data()


@app.exception_handler(Exception)
async def generic_exception_handler(_, exc):
    return JSONResponse(status_code=500, content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": "An internal error occurred."}})


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/health")
def api_health_check():
    return {"status": "ok"}


@app.get("/api")
def api_root():
    return {"message": settings.app_name, "endpoints": ["/api/health", "/api/auth/login", "/api/auth/register", "/api/doctors", "/api/appointments"]}


app.include_router(auth_router)
app.include_router(doctors_router)
app.include_router(appointments_router)
app.include_router(admin_router)
