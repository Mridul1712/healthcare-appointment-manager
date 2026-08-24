from datetime import date, datetime, timedelta, time
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Appointment, AppointmentSlotHold, DoctorLeaveDay, DoctorProfile, DoctorWorkingHour, SlotHoldStatus


def is_slot_available(db: Session, doctor_id: str, start_time: datetime) -> bool:
    end_time = start_time + timedelta(minutes=30)
    appointment_exists = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.start_time == start_time,
            Appointment.status != "CANCELLED",
        )
        .first()
    )
    if appointment_exists:
        return False

    active_hold = (
        db.query(AppointmentSlotHold)
        .filter(
            AppointmentSlotHold.doctor_id == doctor_id,
            AppointmentSlotHold.start_time == start_time,
            AppointmentSlotHold.status == SlotHoldStatus.ACTIVE.value,
            AppointmentSlotHold.expires_at > datetime.utcnow(),
        )
        .first()
    )
    if active_hold:
        return False

    leave_date = (
        db.query(DoctorLeaveDay)
        .filter(DoctorLeaveDay.doctor_id == doctor_id, DoctorLeaveDay.leave_date == start_time.date())
        .first()
    )
    if leave_date:
        return False
    return True


def generate_doctor_slots(db: Session, doctor_id: str, target_date: date, slot_duration_minutes: int | None = None) -> List[datetime]:
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    slot_minutes = slot_duration_minutes or doctor.slot_duration_minutes or 30
    weekday = target_date.weekday()

    working_hours = (
        db.query(DoctorWorkingHour)
        .filter(DoctorWorkingHour.doctor_id == doctor_id, DoctorWorkingHour.weekday == weekday)
        .all()
    )
    if not working_hours:
        return []

    slots: List[datetime] = []
    for work in working_hours:
        start_dt = datetime.combine(target_date, time.fromisoformat(work.start_time))
        end_dt = datetime.combine(target_date, time.fromisoformat(work.end_time))
        cursor = start_dt
        while cursor + timedelta(minutes=slot_minutes) <= end_dt:
            if not is_slot_available(db, doctor_id, cursor):
                cursor += timedelta(minutes=slot_minutes)
                continue
            slots.append(cursor)
            cursor += timedelta(minutes=slot_minutes)

    return sorted(slots)
