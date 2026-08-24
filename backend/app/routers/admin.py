from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import require_roles
from app.models.models import Appointment, AuditLog, DoctorLeaveDay, DoctorProfile, DoctorWorkingHour, Notification, User
from app.schemas import DoctorCreate, DoctorLeaveInput, WorkingHourCreate
from app.services.notifications import EmailService

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/doctors")
def list_doctors(db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    doctors = db.query(DoctorProfile).all()
    return [{
        "id": doctor.id,
        "user_id": doctor.user_id,
        "name": doctor.name,
        "specialization": doctor.specialization,
        "qualification": doctor.qualification,
        "experience_years": doctor.experience_years,
        "slot_duration_minutes": doctor.slot_duration_minutes,
        "is_active": doctor.is_active,
    } for doctor in doctors]


@router.post("/doctors")
def create_doctor(payload: DoctorCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    existing = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Doctor account already exists")

    user = User(email=payload.email.lower().strip(), password_hash=hash_password(payload.password), role="doctor")
    db.add(user)
    db.flush()
    doctor_profile = DoctorProfile(
        user_id=user.id,
        name=payload.full_name,
        specialization=payload.specialization,
        qualification=payload.qualification,
        experience_years=payload.experience_years,
        slot_duration_minutes=payload.slot_duration_minutes,
        is_active=True,
    )
    db.add(doctor_profile)
    db.add(AuditLog(user_id=current_user.id, action="doctor_created", details={"doctor_id": user.id, "specialization": payload.specialization}))
    db.commit()
    return {"id": doctor_profile.id, "name": doctor_profile.name, "specialization": doctor_profile.specialization}


@router.patch("/doctors/{doctor_id}")
def update_doctor(doctor_id: str, payload: DoctorCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor.name = payload.full_name
    doctor.specialization = payload.specialization
    doctor.qualification = payload.qualification
    doctor.experience_years = payload.experience_years
    doctor.slot_duration_minutes = payload.slot_duration_minutes
    db.add(AuditLog(user_id=current_user.id, action="doctor_updated", details={"doctor_id": doctor_id}))
    db.commit()
    return {"id": doctor.id, "status": "updated"}


@router.post("/doctors/{doctor_id}/working-hours")
def create_working_hours(doctor_id: str, payload: WorkingHourCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    row = DoctorWorkingHour(
        doctor_id=doctor_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(row)
    db.commit()
    return {"id": row.id, "doctor_id": doctor_id, "weekday": row.weekday, "start_time": row.start_time, "end_time": row.end_time}


@router.post("/doctors/{doctor_id}/leave")
def add_leave(doctor_id: str, payload: DoctorLeaveInput, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    existing = db.query(DoctorLeaveDay).filter(DoctorLeaveDay.doctor_id == doctor_id, DoctorLeaveDay.leave_date == payload.leave_date).first()
    if existing:
        raise HTTPException(status_code=409, detail="Leave record already exists")

    leave = DoctorLeaveDay(doctor_id=doctor_id, leave_date=payload.leave_date, reason=payload.reason)
    db.add(leave)
    affected = db.query(Appointment).filter(Appointment.doctor_id == doctor_id, Appointment.start_time >= payload.leave_date.strftime("%Y-%m-%d 00:00:00"), Appointment.start_time <= payload.leave_date.strftime("%Y-%m-%d 23:59:59")).all()
    for appointment in affected:
        appointment.status = "DOCTOR_LEAVE"
        patient = db.query(User).filter(User.id == appointment.patient_id).first()
        email_result = EmailService.send_email(
            patient.email if patient else "",
            "Doctor leave notice",
            f"The doctor for your appointment on {payload.leave_date.isoformat()} is unavailable. Please reschedule.",
        ) if patient else {"status": "queued", "recipient": ""}
        db.add(Notification(recipient_user_id=appointment.patient_id, title="Doctor leave notice", body=f"The doctor for your appointment on {payload.leave_date.isoformat()} is unavailable. Please reschedule.", channel="email", status="SENT" if email_result.get("status") == "sent" else "PENDING"))
    db.add(AuditLog(user_id=current_user.id, action="doctor_leave_created", details={"doctor_id": doctor_id, "leave_date": payload.leave_date.isoformat()}))
    db.commit()
    return {"id": leave.id, "doctor_id": doctor_id, "leave_date": leave.leave_date.isoformat(), "reason": leave.reason, "affected_appointments": len(affected)}


@router.delete("/doctors/{doctor_id}/leave/{leave_date}")
def remove_leave(doctor_id: str, leave_date: date, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    leave = db.query(DoctorLeaveDay).filter(DoctorLeaveDay.doctor_id == doctor_id, DoctorLeaveDay.leave_date == leave_date).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    db.delete(leave)
    db.add(AuditLog(user_id=current_user.id, action="doctor_leave_removed", details={"doctor_id": doctor_id, "leave_date": leave_date.isoformat()}))
    db.commit()
    return {"deleted": True}
