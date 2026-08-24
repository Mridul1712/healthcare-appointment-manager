from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import DoctorProfile, DoctorWorkingHour, User
from app.services.availability import generate_doctor_slots

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


@router.get("")
def list_doctors(db: Session = Depends(get_db), specialization: str | None = Query(default=None)):
    query = db.query(DoctorProfile).join(User, DoctorProfile.user_id == User.id).filter(DoctorProfile.is_active == True)
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f"%{specialization}%"))
    doctors = query.all()
    return [{
        "id": doctor.id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "slot_duration_minutes": doctor.slot_duration_minutes,
    } for doctor in doctors]


@router.get("/{doctor_id}")
def get_doctor(doctor_id: str, db: Session = Depends(get_db)):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return {
        "id": doctor.id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "slot_duration_minutes": doctor.slot_duration_minutes,
        "working_hours": [
            {"weekday": item.weekday, "start_time": item.start_time, "end_time": item.end_time}
            for item in doctor.working_hours
        ],
    }


@router.get("/{doctor_id}/availability")
def get_doctor_availability(doctor_id: str, date_value: date = Query(default=date.today(), alias="date"), db: Session = Depends(get_db)):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    slots = generate_doctor_slots(db, doctor_id, date_value, doctor.slot_duration_minutes)
    return {"doctor_id": doctor_id, "date": date_value.isoformat(), "slots": [slot.isoformat() for slot in slots]}
