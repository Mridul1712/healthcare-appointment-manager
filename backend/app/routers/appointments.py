from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import Appointment, AppointmentSlotHold, AuditLog, DoctorProfile, RoleEnum, SlotHoldStatus, Symptom, User
from app.schemas import AppointmentCreate, SlotHoldRequest, SymptomCreate
from app.services.booking import book_appointment, create_slot_hold, expire_slot_holds

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.post("/hold")
def create_appointment_hold(payload: SlotHoldRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != RoleEnum.PATIENT.value:
        raise HTTPException(status_code=403, detail="Only patients can hold slots")
    expire_slot_holds(db)
    hold = create_slot_hold(db, payload.doctor_id, current_user.id, payload.start_time)
    return {"hold_id": hold.id, "doctor_id": hold.doctor_id, "patient_id": hold.patient_id, "start_time": hold.start_time.isoformat(), "expires_at": hold.expires_at.isoformat()}


@router.post("")
def create_appointment(payload: AppointmentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != RoleEnum.PATIENT.value:
        raise HTTPException(status_code=403, detail="Only patients can book appointments")

    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == payload.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    try:
        appointment = book_appointment(db, payload.doctor_id, current_user.id, payload.start_time)
    except HTTPException:
        raise

    db.add(AuditLog(user_id=current_user.id, action="appointment_booked", details={"doctor_id": payload.doctor_id, "start_time": payload.start_time.isoformat()}))
    db.commit()
    return {"id": appointment.id, "doctor_id": appointment.doctor_id, "patient_id": appointment.patient_id, "start_time": appointment.start_time.isoformat(), "status": appointment.status}


@router.get("")
def list_appointments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == RoleEnum.PATIENT.value:
        appointments = db.query(Appointment).filter(Appointment.patient_id == current_user.id).all()
    elif current_user.role == RoleEnum.DOCTOR.value:
        appointments = db.query(Appointment).filter(Appointment.doctor_id == current_user.doctor_profile.id).all()
    else:
        appointments = db.query(Appointment).all()
    return [{"id": a.id, "doctor_id": a.doctor_id, "patient_id": a.patient_id, "status": a.status, "start_time": a.start_time.isoformat()} for a in appointments]


@router.get("/{appointment_id}")
def get_appointment(appointment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if current_user.role == RoleEnum.PATIENT.value and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if current_user.role == RoleEnum.DOCTOR.value and appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    return {"id": appointment.id, "doctor_id": appointment.doctor_id, "patient_id": appointment.patient_id, "status": appointment.status, "start_time": appointment.start_time.isoformat(), "end_time": appointment.end_time.isoformat()}


@router.post("/{appointment_id}/symptoms")
def add_symptoms(appointment_id: str, payload: SymptomCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    symptom = Symptom(
        appointment_id=appointment.id,
        chief_complaint=payload.chief_complaint,
        symptoms=payload.symptoms,
        duration=payload.duration,
        severity=payload.severity,
        additional_notes=payload.additional_notes,
    )
    db.add(symptom)
    db.commit()
    return {"id": symptom.id, "chief_complaint": symptom.chief_complaint}


@router.post("/{appointment_id}/cancel")
def cancel_appointment(appointment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == RoleEnum.PATIENT.value and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if current_user.role == RoleEnum.DOCTOR.value and appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    appointment.status = "CANCELLED"
    db.add(AuditLog(user_id=current_user.id, action="appointment_cancelled", details={"appointment_id": appointment_id}))
    db.commit()
    return {"id": appointment.id, "status": appointment.status}
