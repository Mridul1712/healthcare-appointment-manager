from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.models import (
    Appointment,
    AppointmentSlotHold,
    AppointmentStatus,
    DoctorProfile,
    SlotHoldStatus,
)
from app.services.availability import is_slot_available

settings = get_settings()


def create_slot_hold(db: Session, doctor_id: str, patient_id: str, start_time: datetime) -> AppointmentSlotHold:
    expires_at = datetime.utcnow() + timedelta(minutes=settings.slot_hold_minutes)
    hold = AppointmentSlotHold(
        doctor_id=doctor_id,
        patient_id=patient_id,
        start_time=start_time,
        expires_at=expires_at,
        status=SlotHoldStatus.ACTIVE.value,
    )
    db.add(hold)
    db.commit()
    db.refresh(hold)
    return hold


def expire_slot_holds(db: Session) -> None:
    db.query(AppointmentSlotHold).filter(
        AppointmentSlotHold.status == SlotHoldStatus.ACTIVE.value,
        AppointmentSlotHold.expires_at <= datetime.utcnow(),
    ).update({"status": SlotHoldStatus.EXPIRED.value})
    db.commit()


def book_appointment(db: Session, doctor_id: str, patient_id: str, start_time: datetime) -> Appointment:
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    expire_slot_holds(db)
    try:
        dialect_name = db.bind.dialect.name
        if dialect_name == "postgresql":
            db.execute(text("SELECT id FROM doctor_profiles WHERE id = :doctor_id FOR UPDATE"), {"doctor_id": doctor_id})
    except Exception:
        pass

    if not is_slot_available(db, doctor_id, start_time):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected appointment slot is no longer available. Please refresh availability.",
        )

    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient_id,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=doctor.slot_duration_minutes),
        status=AppointmentStatus.CONFIRMED.value,
    )
    db.add(appointment)
    try:
        db.commit()
        db.refresh(appointment)
        return appointment
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The selected appointment slot is no longer available. Please refresh availability.",
        ) from exc
