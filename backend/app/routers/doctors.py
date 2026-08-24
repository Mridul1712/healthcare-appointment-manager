from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import DoctorProfile, DoctorWorkingHour, User
from app.services.availability import generate_doctor_slots

router = APIRouter(prefix="/api/doctors", tags=["doctors"])


@router.get("")
def list_doctors(db: Session = Depends(get_db), specialization: str | None = Query(default=None), name: str | None = Query(default=None)):
    query = db.query(DoctorProfile).join(User, DoctorProfile.user_id == User.id).filter(DoctorProfile.is_active == True)
    if specialization:
        query = query.filter(DoctorProfile.specialization.ilike(f"%{specialization}%"))
    if name:
        query = query.filter(DoctorProfile.name.ilike(f"%{name}%"))
    doctors = query.all()
    return [{
        "id": doctor.id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "slot_duration_minutes": doctor.slot_duration_minutes,
        "profile_photo_url": doctor.profile_photo_url,
        "bio": doctor.bio,
        "languages": doctor.languages,
        "consultation_fee": doctor.consultation_fee,
        "clinic_name": doctor.clinic_name,
        "status": doctor.status,
        "next_leave_date": doctor.next_leave_date.isoformat() if doctor.next_leave_date else None,
        "return_to_work_date": doctor.return_to_work_date.isoformat() if doctor.return_to_work_date else None,
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
        "profile_photo_url": doctor.profile_photo_url,
        "bio": doctor.bio,
        "languages": doctor.languages,
        "consultation_fee": doctor.consultation_fee,
        "clinic_name": doctor.clinic_name,
        "status": doctor.status,
        "next_leave_date": doctor.next_leave_date.isoformat() if doctor.next_leave_date else None,
        "return_to_work_date": doctor.return_to_work_date.isoformat() if doctor.return_to_work_date else None,
        "working_hours": [
            {"weekday": item.weekday, "start_time": item.start_time, "end_time": item.end_time}
            for item in doctor.working_hours
        ],
        "leave_days": [
            {"id": item.id, "leave_date": item.leave_date.isoformat() if item.leave_date else None, "reason": item.reason}
            for item in doctor.leave_days
        ],
    }


@router.get("/{doctor_id}/availability")
def get_doctor_availability(doctor_id: str, date_value: date = Query(default=date.today(), alias="date"), db: Session = Depends(get_db)):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    slots = generate_doctor_slots(db, doctor_id, date_value, doctor.slot_duration_minutes)
    return {"doctor_id": doctor_id, "date": date_value.isoformat(), "slots": [slot.isoformat() for slot in slots]}
