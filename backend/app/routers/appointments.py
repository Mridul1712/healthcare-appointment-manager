from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.models import Appointment, AppointmentSlotHold, AuditLog, ClinicalNote, DoctorProfile, Notification, PreVisitSummary, Prescription, PrescriptionMedication, PostVisitSummary, RoleEnum, SlotHoldStatus, Symptom, User
from app.schemas import AppointmentCreate, ClinicalNoteCreate, PrescriptionCreate, SlotHoldRequest, SymptomCreate
from app.services.booking import book_appointment, create_slot_hold, expire_slot_holds
from app.services.calendar_service import CalendarService
from app.services.llm_service import generate_post_visit_summary, generate_pre_visit_summary
from app.services.notifications import EmailService

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


def serialize_appointment(appointment: Appointment):
    doctor = appointment.doctor
    return {
        "id": appointment.id,
        "appointment_id": appointment.id,
        "start_time": appointment.start_time.isoformat(),
        "end_time": appointment.end_time.isoformat(),
        "status": appointment.status,
        "doctor": {
            "id": doctor.id if doctor else None,
            "name": doctor.name if doctor else "Doctor",
            "specialization": doctor.specialization if doctor else "",
            "qualification": doctor.qualification,
            "photo": doctor.profile_photo_url if doctor else None,
            "clinic": doctor.clinic_name if doctor else None,
            "experience": doctor.experience_years if doctor else None,
        } if doctor else None,
        "clinic": doctor.clinic_name if doctor else None,
        "symptoms_available": bool(appointment.symptoms),
        "pre_visit_summary_available": bool(appointment.pre_visit_summary),
    }


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

    appointment = book_appointment(db, payload.doctor_id, current_user.id, payload.start_time)
    appointment_end = appointment.start_time + timedelta(minutes=doctor.slot_duration_minutes or 30)
    email_response = EmailService.send_email(
        current_user.email,
        "Appointment booked",
        f"Your appointment with {doctor.name} is confirmed for {appointment.start_time.isoformat()}.",
    )
    calendar_response = CalendarService.create_event_for_appointment(
        doctor.name,
        current_user.patient_profile.full_name if current_user.patient_profile else current_user.email,
        appointment.start_time,
        appointment_end,
    )
    db.add(AuditLog(user_id=current_user.id, action="appointment_booked", details={
        "doctor_id": payload.doctor_id,
        "start_time": payload.start_time.isoformat(),
        "email_status": email_response.get("status"),
        "calendar_status": calendar_response.get("status"),
    }))
    db.add(Notification(recipient_user_id=current_user.id, title="Appointment booked", body=f"Your appointment with {doctor.name} is confirmed for {appointment.start_time.isoformat()}", channel="email", status="SENT" if email_response.get("status") == "sent" else "PENDING"))
    db.commit()
    return {
        "id": appointment.id,
        "doctor_id": appointment.doctor_id,
        "patient_id": appointment.patient_id,
        "start_time": appointment.start_time.isoformat(),
        "status": appointment.status,
        "email": email_response,
        "calendar": calendar_response,
    }


@router.get("")
def list_appointments(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role == RoleEnum.PATIENT.value:
        appointments = db.query(Appointment).filter(Appointment.patient_id == current_user.id).order_by(Appointment.start_time.asc()).all()
    elif current_user.role == RoleEnum.DOCTOR.value:
        appointments = db.query(Appointment).filter(Appointment.doctor_id == current_user.doctor_profile.id).order_by(Appointment.start_time.asc()).all()
    else:
        appointments = db.query(Appointment).order_by(Appointment.start_time.asc()).all()
    return [serialize_appointment(appointment) for appointment in appointments]


@router.get("/{appointment_id}")
def get_appointment(appointment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    if current_user.role == RoleEnum.PATIENT.value and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if current_user.role == RoleEnum.DOCTOR.value and appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    payload = serialize_appointment(appointment)
    payload["patient_id"] = appointment.patient_id
    payload["symptoms"] = [{
        "id": symptom.id,
        "chief_complaint": symptom.chief_complaint,
        "symptoms": symptom.symptoms,
        "duration": symptom.duration,
        "severity": symptom.severity,
        "additional_notes": symptom.additional_notes,
    } for symptom in appointment.symptoms]
    summary = appointment.pre_visit_summary
    if summary:
        payload["pre_visit_summary"] = {
            "id": summary.id,
            "urgency_level": summary.urgency_level,
            "chief_complaint": summary.chief_complaint,
            "suggested_questions": summary.suggested_questions,
            "status": summary.status,
            "provider_response": summary.provider_response,
        }
    else:
        payload["pre_visit_summary"] = None
    return payload


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
    summary_payload = generate_pre_visit_summary(f"{payload.chief_complaint}. {payload.symptoms}. Duration: {payload.duration}. Severity: {payload.severity}. Notes: {payload.additional_notes}")
    summary = PreVisitSummary(
        appointment_id=appointment.id,
        urgency_level=summary_payload.get("urgency_level"),
        chief_complaint=summary_payload.get("chief_complaint"),
        suggested_questions=summary_payload.get("suggested_questions", []),
        provider_response=summary_payload,
        status=summary_payload.get("status", "FAILED"),
    )
    db.add(summary)
    db.commit()
    return {"id": symptom.id, "chief_complaint": symptom.chief_complaint, "summary": summary_payload}


@router.get("/{appointment_id}/pre-visit-summary")
def get_pre_visit_summary(appointment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == RoleEnum.PATIENT.value and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if current_user.role == RoleEnum.DOCTOR.value and appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    summary = db.query(PreVisitSummary).filter(PreVisitSummary.appointment_id == appointment_id).first()
    if not summary:
        return {"status": "PENDING", "message": "No pre-visit summary available yet."}
    return {"urgency_level": summary.urgency_level, "chief_complaint": summary.chief_complaint, "suggested_questions": summary.suggested_questions, "status": summary.status}


@router.post("/{appointment_id}/clinical-notes")
def add_clinical_notes(appointment_id: str, payload: ClinicalNoteCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role != RoleEnum.DOCTOR.value or appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Only the assigned doctor can add notes")

    note = ClinicalNote(appointment_id=appointment.id, note_text=payload.note_text, diagnosis=payload.diagnosis)
    db.add(note)
    db.commit()
    return {"id": note.id, "status": "saved"}


@router.post("/{appointment_id}/prescription")
def create_prescription(appointment_id: str, payload: PrescriptionCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role != RoleEnum.DOCTOR.value or appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Only the assigned doctor can add prescriptions")

    prescription = Prescription(appointment_id=appointment.id, doctor_id=appointment.doctor_id, follow_up_instructions=payload.follow_up_instructions)
    db.add(prescription)
    db.flush()
    for med in payload.medications:
        db.add(PrescriptionMedication(
            prescription_id=prescription.id,
            name=med.name,
            dosage=med.dosage,
            frequency=med.frequency,
            duration=med.duration,
            special_instructions=med.special_instructions,
        ))
    db.commit()
    return {"id": prescription.id, "status": "saved"}


@router.get("/{appointment_id}/post-visit-summary")
def get_post_visit_summary(appointment_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == RoleEnum.PATIENT.value and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if current_user.role == RoleEnum.DOCTOR.value and appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    summary = db.query(PostVisitSummary).filter(PostVisitSummary.appointment_id == appointment_id).first()
    if not summary:
        return {"summary": "No post-visit summary available yet.", "medication_schedule": [], "follow_up_steps": []}
    return {"summary": summary.summary, "medication_schedule": summary.medication_schedule or [], "follow_up_steps": summary.follow_up_steps or []}


@router.post("/{appointment_id}/post-visit-summary")
def create_post_visit_summary(appointment_id: str, payload: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role != RoleEnum.DOCTOR.value or appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Only the assigned doctor can create a summary")

    medication_data = payload.get("medication_schedule", [])
    summary_payload = generate_post_visit_summary(payload.get("summary", "Follow-up instructions documented."), medication_data)
    summary = PostVisitSummary(
        appointment_id=appointment.id,
        summary=summary_payload.get("summary", payload.get("summary", "Follow-up instructions documented.")),
        medication_schedule=summary_payload.get("medication_schedule", medication_data),
        follow_up_steps=summary_payload.get("follow_up_steps", []),
    )
    db.add(summary)
    db.commit()
    return {"status": "saved", "summary": summary_payload}


@router.patch("/{appointment_id}/reschedule")
def reschedule_appointment(appointment_id: str, payload: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if current_user.role == RoleEnum.PATIENT.value and appointment.patient_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    if current_user.role == RoleEnum.DOCTOR.value and appointment.doctor_id != current_user.doctor_profile.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    new_start_time = payload.get("start_time")
    if not new_start_time:
        raise HTTPException(status_code=400, detail="A new start time is required")

    if isinstance(new_start_time, str):
        new_start_time = datetime.fromisoformat(new_start_time)

    if new_start_time <= datetime.utcnow():
        raise HTTPException(status_code=400, detail="The new appointment time must be in the future")

    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == appointment.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    existing = db.query(Appointment).filter(
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.start_time == new_start_time,
        Appointment.id != appointment.id,
        Appointment.status != "CANCELLED",
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The selected appointment slot is no longer available. Please refresh availability.")

    appointment.start_time = new_start_time
    appointment.end_time = new_start_time + timedelta(minutes=doctor.slot_duration_minutes or 30)
    appointment.status = "RESCHEDULED"
    db.add(AuditLog(user_id=current_user.id, action="appointment_rescheduled", details={"appointment_id": appointment_id, "new_start_time": new_start_time.isoformat()}))
    db.commit()
    db.refresh(appointment)
    return serialize_appointment(appointment)


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
