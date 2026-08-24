from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import require_roles
from app.models.models import AuditLog, DoctorLeaveDay, DoctorProfile, User
from app.schemas import DoctorCreate, DoctorLeaveInput

router = APIRouter(prefix="/api/admin", tags=["admin"])


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
    db.add(AuditLog(user_id=current_user.id, action="doctor_leave_created", details={"doctor_id": doctor_id, "leave_date": payload.leave_date.isoformat()}))
    db.commit()
    return {"id": leave.id, "doctor_id": doctor_id, "leave_date": leave.leave_date.isoformat(), "reason": leave.reason}


@router.delete("/doctors/{doctor_id}/leave/{leave_date}")
def remove_leave(doctor_id: str, leave_date: date, db: Session = Depends(get_db), current_user: User = Depends(require_roles("admin"))):
    leave = db.query(DoctorLeaveDay).filter(DoctorLeaveDay.doctor_id == doctor_id, DoctorLeaveDay.leave_date == leave_date).first()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    db.delete(leave)
    db.add(AuditLog(user_id=current_user.id, action="doctor_leave_removed", details={"doctor_id": doctor_id, "leave_date": leave_date.isoformat()}))
    db.commit()
    return {"deleted": True}
